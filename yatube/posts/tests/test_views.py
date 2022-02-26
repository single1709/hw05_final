from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.core.cache import cache

from ..forms import PostForm
from ..models import Post, Group, Comment, Follow

User = get_user_model()


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.author = User.objects.create_user(username='author')
        cls.authorized_client_author = Client()
        cls.authorized_client_author.force_login(cls.author)

        cls.group = Group.objects.create(
            title='Тестовый заголовок группы',
            description='Тестовое описание группы',
            slug='test-slug',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
        )

    def test_pages_uses_correct_template(self):
        """Проверяем, что URL-адрес использует соответствующий шаблон."""

        templates_pages_names = (
            (reverse('posts:index'), 'posts/index.html'),
            (reverse('posts:post_create'), 'posts/create_edit_post.html'),
            (reverse(
                'posts:group_list',
                kwargs={'slug': 'test-slug'}
            ), 'posts/group_list.html'),
            (reverse(
                'posts:profile',
                kwargs={'username': self.author}
            ), 'posts/profile.html'),
            (reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}
            ), 'posts/post_detail.html'),
            (reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.id}
            ), 'posts/create_edit_post.html'),
        )

        for reverse_name, template in templates_pages_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client_author.get(reverse_name)
                self.assertTemplateUsed(response, template)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.author = User.objects.create_user(username='author')
        cls.authorized_client_author = Client()
        cls.authorized_client_author.force_login(cls.author)

        cls.group = Group.objects.create(
            title='Тестовый заголовок группы',
            description='Тестовое описание группы',
            slug='test-slug',
        )

        objs = (Post(
            text=f'Тестовый текст {i}',
            author=cls.author,
            group=cls.group, ) for i in range(13)
        )
        cls.post = Post.objects.bulk_create(objs)

    def test_paginator(self):
        """Проверяем, что Paginator работает корректно"""
        pages_names = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse(
                'posts:profile',
                kwargs={'username': self.author.username}
            ),
        )

        for name_page in pages_names:
            with self.subTest(name_page=name_page):
                response = self.authorized_client_author.get(name_page)
                self.assertEqual(len(response.context['page_obj']), 10)

        for name_page in pages_names:
            with self.subTest(name_page=name_page):
                response = self.authorized_client_author.get(
                    name_page, {'page': 2}
                )
                self.assertEqual(len(response.context['page_obj']), 3)


class ContextViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.author = User.objects.create_user(username='author')
        cls.author2 = User.objects.create_user(username='author2')
        cls.authorized_client_author = Client()
        cls.authorized_client_author.force_login(cls.author2)

        cls.group = Group.objects.create(
            title='Тестовый заголовок группы',
            description='Тестовое описание группы',
            slug='test-slug',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст1',
            author=cls.author2,
            group=cls.group,
        )

    def test_correct_context_index(self):
        """Проверяем context index"""
        response = self.authorized_client_author.get(reverse('posts:index'))
        self.assertIsInstance(response.context['page_obj'][0], Post)

    def test_correct_context_group_list(self):
        """Проверяем context group_list"""
        response = self.authorized_client_author.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertEqual(response.context['group'], self.group)

    def test_correct_context_profile(self):
        """Проверяем context profile"""
        response = self.authorized_client_author.get(
            reverse(
                'posts:profile',
                kwargs={'username': self.author2.username}
            )
        )
        self.assertEqual(response.context['author'], self.author2)

    def test_correct_context_post_detail(self):
        """Проверяем context post_detail"""
        response = self.authorized_client_author.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.context['post'].text, self.post.text)

    def test_correct_context_post_edit(self):
        """Проверяем context post_edit"""
        response = self.authorized_client_author.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(
            response.context['form'].initial['text'],
            self.post.text
        )

    def test_correct_context_post_create(self):
        """Проверяем context post_create"""
        response = self.authorized_client_author.get(
            reverse('posts:post_create')
        )
        self.assertIsInstance(response.context['form'], PostForm)


class CreatePostTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.no_authorized_client = Client()
        cls.author = User.objects.create_user(username='author')
        cls.authorized_client_author = Client()
        cls.authorized_client_author.force_login(cls.author)

        cls.group = Group.objects.create(
            title='Тестовый заголовок группы',
            description='Тестовое описание группы',
            slug='test-slug',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст1',
            author=cls.author,
            group=cls.group,
        )

    def test_correct_post_create_index(self):
        """Проверяем что пост после создания появится на главной странице сайта,
        на странице выбранной группы,в профайле пользователя"""
        pages_names = (
            reverse('posts:index'),
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            ),
            reverse(
                'posts:profile',
                kwargs={'username': self.author.username}
            ),
        )

        for name_page in pages_names:
            with self.subTest(name_page=name_page):
                response = self.authorized_client_author.get(name_page)
                self.assertTrue(
                    response.context['page_obj'][0],
                    'Пост не появился на странице'
                )


class CreateCommentTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.author = User.objects.create_user(username='author')
        cls.authorized_client_author = Client()
        cls.authorized_client_author.force_login(cls.author)

        cls.group = Group.objects.create(
            title='Тестовый заголовок группы',
            description='Тестовое описание группы',
            slug='test-slug',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст1',
            author=cls.author,
            group=cls.group,
        )

    def test_create_comment(self):
        """Проверяем что после успешной отправки комментарий
         появляется на странице поста"""
        comment = Comment.objects.create(
            text='Тестовый текст комментария',
            post=self.post,
            author=self.author,
        )
        response = self.authorized_client_author.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertIn(comment, response.context['comments'])

    def test_comment_authorized_client(self):
        """Проверяем что комментировать посты может
         только авторизованный пользователь"""
        comments_count = Comment.objects.count()

        form_data = {
            'text': 'Тестовый текст комментария 2',
        }

        self.authorized_client_author.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': self.post.id}
            ),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)

        last_comment = Comment.objects.order_by('created').last()
        self.assertEqual(last_comment.text, form_data['text'])
        self.assertEqual(last_comment.author, self.author)


class CacheTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.author = User.objects.create_user(username='author')
        cls.authorized_client_author = Client()
        cls.authorized_client_author.force_login(cls.author)

        cls.group = Group.objects.create(
            title='Тестовый заголовок группы',
            description='Тестовое описание группы',
            slug='test-slug',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст1',
            author=cls.author,
            group=cls.group,
        )

    def test_yes_cache_index(self):
        """Проверяем работу с кешем"""
        posts_count = Post.objects.count()
        response = self.authorized_client_author.get(reverse('posts:index'))
        cache.set('index_page', response.context['page_obj'], 20)

        Post.objects.create(
            text='Тестовый текст2',
            author=self.author,
            group=self.group,
        )
        response = self.authorized_client_author.get(reverse('posts:index'))
        self.assertEqual(len(cache.get(
            'index_page',
            response.context['page_obj'])
        ), posts_count)

        cache.clear()

    def test_no_cache_index(self):
        """Проверяем работу с кешем"""
        posts_count = Post.objects.count()
        response = self.authorized_client_author.get(reverse('posts:index'))
        cache.set('index_page', response.context['page_obj'], 20)

        Post.objects.create(
            text='Тестовый текст2',
            author=self.author,
            group=self.group,
        )

        cache.clear()
        response = self.authorized_client_author.get(reverse('posts:index'))
        self.assertEqual(len(cache.get(
            'index_page',
            response.context['page_obj'])
        ), posts_count + 1)


class FollowTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create_user(username='user')
        cls.author = User.objects.create_user(username='author')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

        cls.group = Group.objects.create(
            title='Тестовый заголовок группы',
            description='Тестовое описание группы',
            slug='test-slug',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст1',
            author=cls.author,
            group=cls.group,
        )

    def test_follow_create(self):
        """Проверяем что авторизованный пользователь может
         подписываться на других пользователей"""
        count_follow = Follow.objects.count()
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author}
            )
        )
        response = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertEqual(Follow.objects.count(), count_follow + 1)
        self.assertEqual(self.author, response.context['page_obj'][0].author)
        self.assertTrue(
            Follow.objects.filter(
                user=self.user,
                author=self.author
            ).exists()
        )

    def test_follow_delete(self):
        """Проверяем что авторизованный пользователь может
        удалять пользователей из подписок"""
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author}
            )
        )
        count_follow = Follow.objects.count()
        Follow.objects.filter(
            user=self.user,
            author=self.author
        ).delete()
        self.assertEqual(Follow.objects.count(), count_follow - 1)
        self.assertFalse(
            Follow.objects.filter(
                user=self.user,
                author=self.author
            ).exists()
        )

    def test_new_post_follow_showing(self):
        """Новая запись пользователя появляется в ленте тех, кто на него
         подписан"""
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author}
            )
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertIn(self.post, response.context['page_obj'])

    def test_new_post_nofollow_showing(self):
        """Новая запись пользователя не появляется
         в ленте тех, кто не подписан"""
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertNotIn(self.post, response.context['page_obj'])

    def test_urls_correct_new_template_404(self):
        """Проверка, что страница 404 отдает кастомный шаблон"""
        response = self.authorized_client.get('unexisting_page/')
        self.assertTemplateUsed(response, 'core/404.html')
