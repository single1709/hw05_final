import tempfile
import shutil

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.db.models.fields.files import ImageFieldFile

from ..models import Post, Group


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TaskCreateFormTests(TestCase):
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
            group=cls.group,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post(self):
        """Проверка формы создания поста"""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        posts_count = Post.objects.count()

        context = {
            'group': self.group.id,
            'text': 'Тестовый текст',
            'image': uploaded
        }

        response = self.authorized_client_author.post(
            reverse('posts:post_create'),
            context,
            follow=True
        )

        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.author.username})
        )
        self.assertEqual(
            Post.objects.count(),
            posts_count + 1
        )

        new_post = Post.objects.order_by('id').last()
        self.assertEqual(new_post.text, self.post.text)
        self.assertEqual(new_post.author, self.post.author)
        self.assertEqual(new_post.group, self.post.group)
        self.assertEqual(new_post.image.name, 'posts/small.gif')
        self.assertIsInstance(new_post.image, ImageFieldFile)

    def test_post_img_context(self):
        pages_with_img = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse(
                'posts:profile',
                kwargs={'username': self.author.username}
            ),
        )

        for page in pages_with_img:
            with self.subTest(page=page):
                response = self.authorized_client_author.get(page)
                self.assertIsInstance(
                    response.context['page_obj'][0].image,
                    ImageFieldFile
                )

        response = self.authorized_client_author.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertIsInstance(response.context['post'].image, ImageFieldFile)

    def test_edit_post(self):
        """Проверка формы редактирования поста"""
        context = {
            'group': self.group.id,
            'text': 'Тестовый текст 2',
        }

        response = self.authorized_client_author.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            context,
        )

        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )

        edit_post = Post.objects.get(id=self.post.id)
        self.assertTrue(edit_post.text, 'Тестовый текст 2')
        self.assertTrue(edit_post.group, self.group.id)
        self.assertTrue(edit_post.author, self.author)