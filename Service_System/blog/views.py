from django.shortcuts import render, redirect, get_object_or_404
from blog.models import Post
from django.contrib.auth.models import User
from django.utils import timezone
from blog.forms import PostForm
from django.contrib.auth.decorators import login_required, user_passes_test
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from blog.serializers import PostSerializer

class blogImage(viewsets.ModelViewSet):
    """
    REST API ViewSet - Admin 권한 필요
    GET(목록/상세): Admin만 가능
    POST(생성): Admin만 가능
    """
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAdminUser]  # Admin만 접근 가능

# Admin 권한 체크 함수
def is_admin(user):
    return user.is_authenticated and user.is_staff

# Create your views here.
@user_passes_test(is_admin, login_url='/admin/login/')
def post_list(request):
    admin = User.objects.get(username='admin')
    posts = Post.objects.filter(author=admin).order_by('-published_date')
    return render(request, 'blog/post_list.html', {'posts': posts})

@user_passes_test(is_admin, login_url='/admin/login/')
def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    return render(request, 'blog/post_detail.html', {'post': post})

@user_passes_test(is_admin, login_url='/admin/login/')
def post_new(request):
    if request.method == "POST":
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.published_date = timezone.now()
            post.save()
            return redirect('post_detail', pk=post.pk)
    else:
        form = PostForm()
    return render(request, 'blog/post_edit.html', {'form': form})

@user_passes_test(is_admin, login_url='/admin/login/')
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == "POST":
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.published_date = timezone.now()
            post.save()
            return redirect('post_detail', pk=post.pk)
    else:
        form = PostForm(instance=post)
    return render(request, 'blog/post_edit.html', {'form': form})
