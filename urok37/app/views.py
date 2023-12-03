import random
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.views.generic import CreateView, DetailView, UpdateView, TemplateView
from .forms import *
from .models import *
from django.core.cache import cache


# Create your views here.

def display_home_page(request):
    return render(request, 'index.html')


class UserLoginView(LoginView):
    template_name = 'login.html'
    form_class = CustomAuthenticationForm  # Проверьте правильность имени формы
    next_page = reverse_lazy('home')

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        if 'test_results' in cache:
            test_results = cache.get('test_results')
            user.Passed_Tests += test_results.get('passed_tests', 0)
            user.Correct_Answers += test_results.get('correct_answers', 0)
            user.Wrong_Answers += test_results.get('wrong_answers', 0)
            cache.delete('test_results')
        user.save()

        return response


class UserSignupView(CreateView):
    model = User
    template_name = 'register.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('home')


class UserProfileView(DetailView):
    model = User
    template_name = 'profile.html'
    context_object_name = 'profile'
    pk_url_kwarg = 'user_id'


def perform_logout(request):
    logout(request)
    return redirect('home')


class UserPasswordUpdateView(PasswordChangeView):
    template_name = 'change_password.html'
    form_class = UserPasswordChangeForm
    success_url = reverse_lazy('home')


class UserProfileEditView(UpdateView):
    model = User
    template_name = 'change_profile.html'
    form_class = UserProfileUpdateForm
    success_url = reverse_lazy('home')
    pk_url_kwarg = 'user_id'


class QuestionCreationView(CreateView):
    model = Question
    template_name = 'add_question.html'
    form_class = NewQuestionForm
    success_url = reverse_lazy('home')


test_questions = []


from django.core.cache import cache
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Question, Like, User
import random
from django.core.cache import cache
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Question, Like, User
import random

class CharacterQuizView(TemplateView):
    template_name = 'test.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.request.user.id if self.request.user.is_authenticated else 'anonymous'

        # Получение вопросов из кэша
        quiz_questions = cache.get(f'quiz_questions_{user_id}')

        if not quiz_questions:
            questions = list(Question.objects.all())
            if len(questions) < 10:
                quiz_questions = questions
            else:
                quiz_questions = random.sample(questions, 10)
            cache.set(f'quiz_questions_{user_id}', quiz_questions, timeout=3600)

        context['quiz_questions'] = quiz_questions
        return context

    def post(self, request, *args, **kwargs):
        user_id = self.request.user.id if request.user.is_authenticated else 'anonymous'
        test_questions = cache.get(f'quiz_questions_{user_id}')

        if 'like_question' in request.POST:
            self.handle_like(request)

        if test_questions:
            return self.evaluate_answers(request, test_questions)
        else:
            return redirect('some_error_page')  # Перенаправление на страницу ошибки

    def handle_like(self, request):
        if request.user.is_authenticated:
            question_id = request.POST.get('like')
            question = get_object_or_404(Question, id=question_id)
            like, created = Like.objects.get_or_create(user=request.user, question=question)

            if not created:
                question.likes_count -= 1
                like.delete()
            else:
                question.likes_count += 1

            question.save()

    def evaluate_answers(self, request, test_questions):
        right_answers = 0
        wrong_answers = 0
        perfect_test = False

        for question in test_questions:
            if question.right_answer == request.POST.get(f"answers_{question.id}"):
                right_answers += 1
            else:
                wrong_answers += 1

        if request.user.is_authenticated:
            user = request.user
            user.Passed_Tests += 1
            user.Correct_Answers += right_answers
            user.Wrong_Answers += wrong_answers

            if len(test_questions) == 10:
                if right_answers >= 7:
                    user.Perfect_Tests += 1
                    perfect_test = True
            else:
                if right_answers >= len(test_questions) // 2:
                    user.Perfect_Tests += 1
                    perfect_test = True

            user.save()

            test_results = {
                'right_answers': right_answers,
                'wrong_answers': wrong_answers,
                'perfect_test': perfect_test,
            }
            cache.set(f'test_results_{user.username}', test_results, timeout=3600)
        else:
            test_results = {
                'right_answers': right_answers,
                'wrong_answers': wrong_answers,
                'perfect_test': right_answers == len(test_questions),
            }
            cache.set(f'test_results_{user_id}', test_results, timeout=3600)

        next_question_url = reverse('test') + f'?question_id={",".join(str(question.id) for question in test_questions)}'
        return redirect(next_question_url)


def test_results_view(request, user_id):
    # Извлекаем результаты теста из кэша
    user_key = f'test_results_{user_id}'
    test_results = cache.get(user_key)

    if not test_results:
        # Обработка случая, когда результаты теста не найдены в кэше
        return render(request, 'test_results_error.html')

    # Отображение страницы с результатами теста
    return render(request, 'test_results.html', {'test_results': test_results})


from django.shortcuts import render, get_object_or_404
from django.core.cache import cache
from .models import User


from django.shortcuts import render
from django.core.cache import cache
from .models import Question, Like, Journal

def home_view(request):
    data = cache.get('home_page_data')
    if not data:
        data = {
            'question': Question.objects.all(),
            'like': Like.objects.all(),
            'journal': Journal.objects.all(),
        }
        cache.set('home_page_data', data, timeout=10)

    return render(request, 'index.html', data)



def profile_view(request, user_id):
    # Получение профиля пользователя
    user = get_object_or_404(User, pk=user_id)

    # Попытка получить данные профиля пользователя из кэша
    profile_data = cache.get(f'profile_data_{user_id}')

    if not profile_data:
        profile_data = User.objects.all()  # Замените на ваш метод получения данных
        cache.set(f'profile_data_{user_id}', profile_data, timeout=3600)

    return render(request, 'profile.html', {'profile': user, 'data': profile_data})


