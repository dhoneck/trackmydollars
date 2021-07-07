from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import BudgetPeriod

CHOICES = (
    (1, 'Jan'),
    (2, 'Feb'),
    (3, 'Mar'),
    (4, 'Apr'),
    (5, 'May'),
    (6, 'Jun'),
    (7, 'Jul'),
    (8, 'Aug'),
    (9, 'Sep'),
    (10, 'Oct'),
    (11, 'Nov'),
    (12, 'Dec'),
)


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ("email",)


class BudgetPeriodForm(forms.Form):
    month = forms.ChoiceField(choices=CHOICES)
    year = forms.IntegerField()
    starting_bank_balance = forms.DecimalField(max_digits=9, decimal_places=2, required=True)
    usable_balance = forms.DecimalField(max_digits=9, decimal_places=2, required=True)

    def __init__(self, *args, **kwargs):
        print('KWARGS:', kwargs)
        print('ARGS:', args)
        self.user = kwargs.pop('user')
        print('USER IN FORM:', self.user)
        super(BudgetPeriodForm, self).__init__(*args, **kwargs)
        self.fields['template'] = forms.ModelChoiceField(required=False, queryset=BudgetPeriod.objects.filter(user_id=self.user).order_by('-month', '-year'))


class DateForm(forms.Form):
    date = forms.DateTimeField(input_formats=['%Y-%m-%d'])