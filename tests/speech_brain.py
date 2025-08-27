#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import glob
import time
import argparse
import numpy as np
import librosa
import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector
import torch
from speechbrain.inference.speaker import EncoderClassifier

# ---- Config via env or edit here ----
PG_DSN = os.getenv(
    "POSTGRES_CONNECTION",
    "postgresql://postgres:postgres@localhost:5432/postgres"
)
TABLE_NAME = os.getenv("VOICE_TABLE", "voice_embeddings")
INDEX_TYPE = os.getenv("VOICE_INDEX", "ivfflat")  # or "hnsw"
IVFFLAT_LISTS = int(os.getenv("IVFFLAT_LISTS", "100"))  # tune later
MODEL_SOURCE = "speechbrain/spkrec-ecapa-voxceleb"

# ---- Model init (ECAPA-TDNN) ----
# SpeechBrain model trained on VoxCeleb; cosine is the default scoring.  
_classifier = None

def get_classifier():
    global _classifier
    if _classifier is None:
        _classifier = EncoderClassifier.from_hparams(source=MODEL_SOURCE, run_opts={"device": "cpu"})
    return _classifier

def load_audio_mono16k(path: str):
    # Resample/mono at load; librosa returns float32 in [-1,1]
    y, sr = librosa.load(path, sr=16000, mono=True)
    return y, 16000

@torch.inference_mode()
def embed_file(path: str) -> np.ndarray:
    clf = get_classifier()
    y, sr = load_audio_mono16k(path)
    wav = torch.from_numpy(y).unsqueeze(0)  # (1, T)
    emb = clf.encode_batch(wav)  # shape: (1, 1, D) or (1, D)
    emb = emb.squeeze().cpu().numpy().astype(np.float32)
    # L2-normalize for cosine; ECAPA outputs are typically already well-behaved,
    # but normalization keeps distances consistent for pgvector cosine.
    norm = np.linalg.norm(emb)
    if norm > 0:
        emb = emb / norm
    return emb

def connect():
    conn = psycopg.connect(PG_DSN, row_factory=dict_row)
    register_vector(conn)  # enables numpy <-> pgvector
    return conn

def ensure_schema(conn, dim: int):
    with conn.cursor() as cur:
        # Enable extension
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        # Create table with discovered dimension
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id BIGSERIAL PRIMARY KEY,
                label TEXT,
                file_path TEXT UNIQUE,
                duration_s REAL,
                sr INT,
                embedding VECTOR({dim}),
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """)
        # Create index for cosine distance; use IVFFLAT or HNSW
        if INDEX_TYPE.lower() == "hnsw":
            # HNSW: fast & strong recall in pgvector 0.7+  :contentReference[oaicite:7]{index=7}
            cur.execute(f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_indexes 
                        WHERE schemaname = current_schema() AND indexname = '{TABLE_NAME}_hnsw_cos_idx'
                    ) THEN
                        EXECUTE 'CREATE INDEX {TABLE_NAME}_hnsw_cos_idx ON {TABLE_NAME} USING hnsw (embedding vector_cosine_ops)';
                    END IF;
                END$$;
            """)
        else:
            cur.execute(f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_indexes 
                        WHERE schemaname = current_schema() AND indexname = '{TABLE_NAME}_ivf_cos_idx'
                    ) THEN
                        EXECUTE 'CREATE INDEX {TABLE_NAME}_ivf_cos_idx ON {TABLE_NAME} USING ivfflat (embedding vector_cosine_ops) WITH (lists = {IVFFLAT_LISTS})';
                    END IF;
                END$$;
            """)
    conn.commit()

def upsert_embedding(conn, label: str, file_path: str, duration_s: float, sr: int, emb: np.ndarray):
    with conn.cursor() as cur:
        cur.execute(f"""
            INSERT INTO {TABLE_NAME}(label, file_path, duration_s, sr, embedding)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (file_path) DO UPDATE
              SET label = EXCLUDED.label,
                  duration_s = EXCLUDED.duration_s,
                  sr = EXCLUDED.sr,
                  embedding = EXCLUDED.embedding,
                  created_at = now()
            RETURNING id;
        """, (label, file_path, float(duration_s), int(sr), emb))
        row = cur.fetchone()
    conn.commit()
    return row["id"]

def ingest_dir(args):
    paths = []
    for ext in ("*.wav", "*.mp3", "*.flac", "*.m4a", "*.ogg"):
        paths.extend(glob.glob(os.path.join(args.input, "**", ext), recursive=True))
    if not paths:
        print("No audio files found.")
        return

    # Peek dim from first file
    first_emb = embed_file(paths[0])
    dim = int(first_emb.shape[-1])
    conn = connect()
    ensure_schema(conn, dim)

    # optional bulk setting for IVFFLAT recall/speed
    with conn.cursor() as cur:
        cur.execute("SET LOCAL ivfflat.probes = %s;", (max(1, int(np.sqrt(max(1, IVFFLAT_LISTS)))),))

    # Insert first one
    y, sr = load_audio_mono16k(paths[0])
    upsert_embedding(conn, args.label, os.path.abspath(paths[0]), len(y)/sr, sr, first_emb)

    # Rest
    for p in paths[1:]:
        emb = embed_file(p)
        y, sr = load_audio_mono16k(p)
        upsert_embedding(conn, args.label, os.path.abspath(p), len(y)/sr, sr, emb)

    print(f"Ingested {len(paths)} files into {TABLE_NAME} (dim={dim}).")

def search_file(args):
    # Compute query embedding
    q = embed_file(args.query)
    dim = int(q.shape[-1])
    conn = connect()
    ensure_schema(conn, dim)

    with conn.cursor() as cur:
        # cosine distance operator <=> ; smaller is closer  :contentReference[oaicite:8]{index=8}
        cur.execute(
            f"""
            SELECT id, label, file_path, duration_s,
                   (embedding <=> %s) AS cosine_distance
            FROM {TABLE_NAME}
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            (q, q, args.k),
        )
        rows = cur.fetchall()

    print(f"Top {args.k} nearest by cosine distance:")
    for r in rows:
        print(f"[{r['id']}] d={r['cosine_distance']:.4f}  label={r['label'] or '-'}  file={r['file_path']}")

def enroll_centroids(args):
    """
    Optional: build/refresh per-speaker centroids (averages) into a second table for crisp verification thresholds.
    """
    conn = connect()
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS voice_speakers (
                speaker TEXT PRIMARY KEY,
                embedding VECTOR(192),         -- WILL be altered to the correct dim below
                examples INT DEFAULT 0,
                updated_at TIMESTAMPTZ DEFAULT now()
            )
        """)
        # discover true dim from any row in voice_embeddings
        cur.execute(f"SELECT (embedding)::text FROM {TABLE_NAME} LIMIT 1;")
        row = cur.fetchone()
        if row and row["embedding"]:
            dim = len(row["embedding"].strip("[]").split(","))
            cur.execute("DROP TABLE IF EXISTS voice_speakers CASCADE")
            cur.execute(f"""
                CREATE TABLE voice_speakers (
                    speaker TEXT PRIMARY KEY,
                    embedding VECTOR({dim}),
                    examples INT DEFAULT 0,
                    updated_at TIMESTAMPTZ DEFAULT now()
                )
            """)
            # average per label
            cur.execute(f"""
                INSERT INTO voice_speakers (speaker, embedding, examples)
                SELECT label AS speaker,
                       AVG(embedding) AS embedding,
                       COUNT(*)
                FROM {TABLE_NAME}
                WHERE label IS NOT NULL AND label <> ''
                GROUP BY label
            """)
            # cosine index
            cur.execute("""
                CREATE INDEX IF NOT EXISTS voice_speakers_ivf_cos_idx
                ON voice_speakers USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50)
            """)
            conn.commit()
            print("Rebuilt voice_speakers centroids.")
        else:
            print("No embeddings yet; nothing to build.")

def verify_against_centroids(args):
    """Binary same/different by comparing query to speaker centroids."""
    q = embed_file(args.query)
    conn = connect()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT speaker, (embedding <=> %s) AS cosine_distance
            FROM voice_speakers
            ORDER BY embedding <=> %s LIMIT 5
        """, (q, q))
        rows = cur.fetchall()
    print("Nearest speakers:")
    for r in rows:
        print(f"{r['speaker']}: d={r['cosine_distance']:.4f}")
    print("\nNote: choose a threshold on a dev set; ~0.2–0.3 cosine distance is a common ballpark, "
          "but calibrate on YOUR mic/room/data.")

def main():
    ap = argparse.ArgumentParser(description="Voice embeddings with ECAPA + pgvector")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_ing = sub.add_parser("ingest", help="Ingest a folder of audio files")
    p_ing.add_argument("-i", "--input", required=True, help="Folder with audio")
    p_ing.add_argument("-l", "--label", default="", help="Optional label/speaker name for all files")
    p_ing.set_defaults(func=ingest_dir)

    p_search = sub.add_parser("search", help="Find nearest matches for a file")
    p_search.add_argument("-q", "--query", required=True, help="Audio file to search by")
    p_search.add_argument("-k", "--k", type=int, default=5, help="Neighbors to return")
    p_search.set_defaults(func=search_file)

    p_cent = sub.add_parser("build-centroids", help="Average embeddings per label")
    p_cent.set_defaults(func=enroll_centroids)

    p_ver = sub.add_parser("verify", help="Compare a file to speaker centroids")
    p_ver.add_argument("-q", "--query", required=True)
    p_ver.set_defaults(func=verify_against_centroids)

    args = ap.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
