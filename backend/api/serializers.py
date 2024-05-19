from django.contrib.auth.validators import UnicodeUsernameValidator
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import exceptions, serializers
from rest_framework.validators import UniqueValidator

from .fields import Base64ImageField
from .validators import validate_username
from core.enums import Length
from recipes.models import (
    Favorite, Ingredient, Recipe, RecipeIngredient, Tag, ShoppingCart
)
from users.models import User, Subscription


SUBSCRIPTION_NOT_FOUND_ERROR = 'Подписка не найдена'
RE_SUBSCRIPTION_VALIDATION_ERROR = 'Нельзя подписаться ещё раз'
ME_SUBSCRIPTION_VALIDATION_ERROR = 'Нельзя подписаться на самого себя'
RECIPE_VALIDATION_ERROR = 'Рецепт уже в корзине.'
INGREDIENTS_NOT_FOUND_ERROR = 'Количество ингредиентов не должно быть равно 0.'
RECIPE_NOT_FOUND_VALIDATION_ERROR = 'Рецепт не найден в корзине.'
RECIPE_VALIDATION_ERROR_FAVORITES = 'Рецепт уже добавлен в избранное.'
NOT_FOUND_FIELDS_ERROR = 'Не хватает поля тэгов или ингредиентов.'


class UserGetSerializer(UserSerializer):

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed'
        )
        read_only_fields = ('id', 'is_subscribed')

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        return user.is_authenticated and obj.subscription.filter(
            user=user
        ).exists()


class UserCreatesSerializer(UserCreateSerializer):
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all())])
    username = serializers.CharField(
        max_length=Length.MAX_LENGTH_USERNAME.value,
        validators=[
            UniqueValidator(queryset=User.objects.all()),
            UnicodeUsernameValidator(),
            validate_username
        ]
    )

    class Meta:
        model = User
        fields = (
            'email', 'id', 'password', 'username', 'first_name', 'last_name')
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True},
            'password': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class RecipeMiniSerializer(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubcriptionSerializer(UserGetSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count'
        )

    def get_recipes(self, user):
        request = self.context.get('request')
        queryset = Recipe.objects.filter(author=user)
        if request and not request.user.is_anonymous:
            recipes_limit = request.query_params.get('recipes_limit')
            if recipes_limit:
                try:
                    queryset = queryset[:int(recipes_limit)]
                except TypeError:
                    pass
        return RecipeMiniSerializer(
            queryset, many=True, context=self.context
        ).data

    def get_recipes_count(self, user):
        return Recipe.objects.filter(author=user).count()


class SubscriptionCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Subscription
        fields = ('user', 'author')

    def validate(self, data):
        user = self.context['request'].user
        author = data.get('author')
        if self.context['request'].method == 'POST':
            if author == user:
                raise exceptions.ValidationError(
                    ME_SUBSCRIPTION_VALIDATION_ERROR
                )
            if Subscription.objects.filter(
                user=user, author=author
            ).exists():
                raise exceptions.ValidationError(
                    RE_SUBSCRIPTION_VALIDATION_ERROR
                )
        if self.context['request'].method == 'DELETE':
            try:
                Subscription.objects.get(
                    author=author, user=user
                )
            except Subscription.DoesNotExist:
                raise serializers.ValidationError(
                    SUBSCRIPTION_NOT_FOUND_ERROR
                )
        return data

    def to_representation(self, instance):
        request = self.context.get('request')
        return SubcriptionSerializer(
            instance=instance.user,
            context={'request': request}
        ).data


class RecipeIngredientPostSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
    )
    amount = serializers.IntegerField(
        write_only=True,
        min_value=Length.MIN_AMOUNT_OF_INGREDIENTS.value,
        max_value=Length.MAX_AMOUNT_OF_INGREDIENTS.value
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeIngredientGetSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')

    def to_internal_value(self, data):
        if isinstance(data, dict):
            ingredient_id = data.get('id')
            amount = data.get('amount')
            if ingredient_id is not None:
                return {'id': ingredient_id, 'amount': amount}
        return super().to_internal_value(data)


class RecipeGetSerializer(serializers.ModelSerializer):

    tags = TagSerializer(many=True)
    author = UserGetSerializer(read_only=True)
    ingredients = RecipeIngredientGetSerializer(
        many=True, required=True, source='ingredients_recipe'
    )
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField(
        method_name='get_image_url',
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'name', 'text',
            'cooking_time', 'image', 'is_favorited', 'is_in_shopping_cart'
        )

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and user.favorite_user.filter(
            recipe=obj.id
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and user.shopping_cart.filter(
            recipe=obj.id
        ).exists()

    def get_image_url(self, obj):
        return obj.image.url


class RecipePostSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientPostSerializer(
        many=True, required=True,
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=True
    )
    image = Base64ImageField()
    author = UserGetSerializer(read_only=True)
    cooking_time = serializers.IntegerField(
        min_value=Length.MIN_COOKING_TIME.value,
        max_value=Length.MAX_COOKING_TIME.value
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'name', 'text', 'cooking_time', 'image',
        )

    def validate(self, data):
        ingredients_data = data.get('ingredients')
        if not ingredients_data:
            raise exceptions.ValidationError(
                {'ingredients': 'Должен быть хотя бы один ингредиент.'}
            )
        ingredient_id = [ingredient['id'] for ingredient in ingredients_data]
        if len(ingredient_id) != len(set(ingredient_id)):
            raise exceptions.ValidationError(
                {'ingredients': 'Ингредиенты не могут повторяться.'}
            )
        tags_data = data.get('tags')
        if not tags_data:
            raise exceptions.ValidationError(
                {'tags': 'Должен быть хотя бы один тег.'}
            )
        if len(tags_data) != len(set(tags_data)):
            raise exceptions.ValidationError(
                {'tags': 'Теги не могут повторяться.'}
            )
        return data

    def create_ingredients_amounts(self, ingredients_data, recipe):
        recipe_ingredients = []
        for ingredient in ingredients_data:
            recipe_ingredients.append(
                RecipeIngredient(
                    recipe=recipe,
                    ingredient=ingredient['id'],
                    amount=ingredient['amount']
                )
            )
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        validated_data['author'] = self.context['request'].user
        recipe = super().create(validated_data)
        recipe.tags.set(tags_data)
        self.create_ingredients_amounts(ingredients_data, recipe)
        return recipe

    def update(self, instance, validated_data):
        tags_data = validated_data.pop('tags')
        instance.tags.clear()
        instance.tags.set(tags_data)
        ingredients_data = validated_data.pop('ingredients')
        ingredients_recipe = instance.ingredients_recipe.all()
        ingredients_recipe.delete()
        self.create_ingredients_amounts(
            recipe=instance, ingredients_data=ingredients_data
        )
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeGetSerializer(
            instance,
            context={'request': self.context.get('request')}
        ).data


class FavoriteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Favorite
        fields = ('user', 'recipe')

    def validate(self, data):
        user = self.context['request'].user
        recipe = data['recipe']
        favorite = user.favorite_user.filter(
            recipe=recipe
        ).exists()
        if self.context['request'].method == 'POST' and favorite:
            raise serializers.ValidationError(
                'Рецепт уже в избранном'
            )
        if self.context['request'].method == 'DELETE' and not favorite:
            raise serializers.ValidationError(
                'Ошибка. Рецепт уже был удалён.'
            )
        return data

    def to_representation(self, instance):
        return RecipeMiniSerializer(
            instance=instance.recipe,
        ).data


class ShoppingCartSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')

    def validate(self, data):
        user = self.context['request'].user
        recipe = data['recipe']
        shopping_cart = user.shopping_cart.filter(
            recipe=recipe
        ).exists()
        if self.context['request'].method == 'POST' and shopping_cart:
            raise serializers.ValidationError(
                'Рецепт уже в корзине'
            )
        if self.context['request'].method == 'DELETE' and not shopping_cart:
            raise serializers.ValidationError(
                'Ошибка. Рецепт уже был удалён.'
            )
        return data

    def to_representation(self, instance):
        return RecipeMiniSerializer(
            instance=instance.recipe,
        ).data
