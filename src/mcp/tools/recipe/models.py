"""
Recipe data models.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


class Ingredient:
    """
    Ingredient model.
    """

    def __init__(
        self,
        name: str,
        quantity: Optional[float] = None,
        unit: Optional[str] = None,
        text_quantity: str = "",
        notes: str = "",
    ):
        self.name = name
        self.quantity = quantity
        self.unit = unit
        self.text_quantity = text_quantity
        self.notes = notes

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a dictionary.
        """
        return {
            "name": self.name,
            "quantity": self.quantity,
            "unit": self.unit,
            "text_quantity": self.text_quantity,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Ingredient":
        """
        Create an ingredient from a dictionary.
        """
        return cls(
            name=data.get("name", ""),
            quantity=data.get("quantity"),
            unit=data.get("unit"),
            text_quantity=data.get("text_quantity", ""),
            notes=data.get("notes", ""),
        )


class Step:
    """
    Cooking step model.
    """

    def __init__(self, step: int, description: str):
        self.step = step
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a dictionary.
        """
        return {"step": self.step, "description": self.description}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Step":
        """
        Create a step from a dictionary.
        """
        return cls(step=data.get("step", 0), description=data.get("description", ""))


class Recipe:
    """
    Recipe model.
    """

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        category: str,
        difficulty: int = 1,
        tags: List[str] = None,
        servings: int = 1,
        ingredients: List[Ingredient] = None,
        steps: List[Step] = None,
        image_path: Optional[str] = None,
        images: List[str] = None,
        source_path: str = "",
        prep_time_minutes: Optional[int] = None,
        cook_time_minutes: Optional[int] = None,
        total_time_minutes: Optional[int] = None,
        additional_notes: List[str] = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.category = category
        self.difficulty = difficulty
        self.tags = tags or []
        self.servings = servings
        self.ingredients = ingredients or []
        self.steps = steps or []
        self.image_path = image_path
        self.images = images or []
        self.source_path = source_path
        self.prep_time_minutes = prep_time_minutes
        self.cook_time_minutes = cook_time_minutes
        self.total_time_minutes = total_time_minutes
        self.additional_notes = additional_notes or []

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a dictionary.
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "difficulty": self.difficulty,
            "tags": self.tags,
            "servings": self.servings,
            "ingredients": [ing.to_dict() for ing in self.ingredients],
            "steps": [step.to_dict() for step in self.steps],
            "image_path": self.image_path,
            "images": self.images,
            "source_path": self.source_path,
            "prep_time_minutes": self.prep_time_minutes,
            "cook_time_minutes": self.cook_time_minutes,
            "total_time_minutes": self.total_time_minutes,
            "additional_notes": self.additional_notes,
        }

    def to_simple_dict(self) -> Dict[str, Any]:
        """
        Convert to a simplified dictionary, including id, name, description, and ingredients.
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "ingredients": [
                {"name": ing.name, "text_quantity": ing.text_quantity}
                for ing in self.ingredients
            ],
        }

    def to_name_only_dict(self) -> Dict[str, Any]:
        """
        Convert to a dictionary containing only name and description.
        """
        return {"name": self.name, "description": self.description}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Recipe":
        """
        Create a recipe from a dictionary.
        """
        ingredients = [Ingredient.from_dict(ing) for ing in data.get("ingredients", [])]
        steps = [Step.from_dict(step) for step in data.get("steps", [])]

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            category=data.get("category", ""),
            difficulty=data.get("difficulty", 1),
            tags=data.get("tags", []),
            servings=data.get("servings", 1),
            ingredients=ingredients,
            steps=steps,
            image_path=data.get("image_path"),
            images=data.get("images", []),
            source_path=data.get("source_path", ""),
            prep_time_minutes=data.get("prep_time_minutes"),
            cook_time_minutes=data.get("cook_time_minutes"),
            total_time_minutes=data.get("total_time_minutes"),
            additional_notes=data.get("additional_notes", []),
        )


class PaginatedResult:
    """
    Paginated result model.
    """

    def __init__(
        self,
        data: List[Any],
        page: int,
        page_size: int,
        total_records: int,
        total_pages: int,
    ):
        self.data = data
        self.page = page
        self.page_size = page_size
        self.total_records = total_records
        self.total_pages = total_pages

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a dictionary.
        """
        return {
            "data": self.data,
            "pagination": {
                "page": self.page,
                "page_size": self.page_size,
                "total_records": self.total_records,
                "total_pages": self.total_pages,
            },
        }


class RecipeSession:
    """
    Recipe session model for caching recipe data.
    """

    def __init__(self, session_id: str = None):
        self.id = session_id or str(uuid.uuid4())
        self.recipes: Dict[str, Recipe] = {}
        self.categories: List[str] = []
        self.created_at = datetime.now().isoformat()
        self.last_accessed = datetime.now().isoformat()

    def add_recipe(self, recipe: Recipe) -> None:
        """
        Add a recipe to the session.
        """
        self.recipes[recipe.id] = recipe
        self.last_accessed = datetime.now().isoformat()

    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        """
        Get a recipe from the session.
        """
        self.last_accessed = datetime.now().isoformat()
        return self.recipes.get(recipe_id)

    def add_recipes(self, recipes: List[Recipe]) -> None:
        """
        Add recipes in bulk.
        """
        for recipe in recipes:
            self.recipes[recipe.id] = recipe
        self.last_accessed = datetime.now().isoformat()

    def set_categories(self, categories: List[str]) -> None:
        """
        Set the category list.
        """
        self.categories = categories
        self.last_accessed = datetime.now().isoformat()

    def search_recipes(self, query: str) -> List[Recipe]:
        """
        Search for recipes, supports fuzzy matching.
        """
        query_lower = query.lower()
        results = []

        for recipe in self.recipes.values():
            # Check name
            if query_lower in recipe.name.lower():
                results.append(recipe)
                continue

            # Check description
            if query_lower in recipe.description.lower():
                results.append(recipe)
                continue

            # Check ingredients
            for ingredient in recipe.ingredients:
                if query_lower in ingredient.name.lower():
                    results.append(recipe)
                    break

        return results

    def get_recipes_by_category(self, category: str) -> List[Recipe]:
        """
        Get recipes by category.
        """
        return [
            recipe for recipe in self.recipes.values() if recipe.category == category
        ]

    def clear_recipes(self) -> None:
        """
        Clear the recipe cache.
        """
        self.recipes.clear()
        self.last_accessed = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a dictionary.
        """
        return {
            "id": self.id,
            "recipes": {k: v.to_dict() for k, v in self.recipes.items()},
            "categories": self.categories,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
        }
