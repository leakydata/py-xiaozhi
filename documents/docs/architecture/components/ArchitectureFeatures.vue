<script setup lang="ts">
import {
  ArrowsRightLeftIcon,
  BoltIcon,
  CubeIcon,
  PuzzlePieceIcon,
  ShareIcon
} from '@heroicons/vue/24/solid';
// Architecture Features
const architectureFeatures = [
  {
    title: 'Singleton Pattern',
    description: 'The application core uses a thread-safe singleton pattern to ensure a single global instance',
    icon: CubeIcon
  },
  {
    title: 'Asynchronous Architecture',
    description: 'Fully adopts asyncio for asynchronous programming, supporting high concurrency and high performance',
    icon: BoltIcon
  },
  {
    title: 'Resource Management',
    description: 'Centralized resource manager for dependency tracking and graceful cleanup',
    icon: ShareIcon
  },
  {
    title: 'State Machine Pattern',
    description: 'Device state management uses a state machine pattern for clear state transition logic',
    icon: ArrowsRightLeftIcon
  },
  {
    title: 'Plugin-based Design',
    description: 'MCP tools and IoT devices use a plugin-based design, supporting dynamic extension',
    icon: PuzzlePieceIcon
  },
  {
    title: 'Cross-platform Compatibility',
    description: 'Supports multiple platforms including Windows, macOS, and Linux with graceful degradation',
    icon: CubeIcon
  }
];

const featureColors = [
  'bg-blue-500',
  'bg-indigo-500',
  'bg-purple-500',
  'bg-pink-500',
  'bg-red-500'
];
</script>

<template>
  <div class="bg-white rounded-lg relative mb-10">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="(feature, index) in architectureFeatures" :key="index"
          class="bg-white rounded-lg p-6 hover:shadow-xl transition-shadow">
          <div class="w-12 h-12 rounded-full flex items-center justify-center mb-4"
            :class="featureColors[index % featureColors.length]">
            <component :is="feature.icon" class="w-6 h-6 text-white" />
          </div>
          <h3 class="text-xl font-semibold mb-2">{{ feature.title }}</h3>
          <p class="text-gray-700">{{ feature.description }}</p>
        </div>
      </div>
    </div>
</template>

<style scoped>
/* Architecture features card style optimization */
.grid-cols-1.md\:grid-cols-2.lg\:grid-cols-3 > div {
  transition: all 0.3s ease;
  height: 100%;
}

.grid-cols-1.md\:grid-cols-2.lg\:grid-cols-3 > div:hover {
  transform: translateY(-5px);
}
</style>