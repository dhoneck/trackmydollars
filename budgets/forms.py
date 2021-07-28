from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import BudgetPeriod, ExpenseTransaction

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
    add_money_schedule_items = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(BudgetPeriodForm, self).__init__(*args, **kwargs)
        self.fields['template'] = forms.ModelChoiceField(required=False, queryset=BudgetPeriod.objects.filter(user_id=self.user).order_by('-month', '-year'))


class DateForm(forms.Form):
    date = forms.DateTimeField(input_formats=['%Y-%m-%d'])


class ExpenseTransactionForm(forms.ModelForm):
    class Meta:
        model = ExpenseTransaction
        exclude = ['user', 'credit_payoff']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(ExpenseTransactionForm, self).__init__(*args, **kwargs)


class ExpenseTransactionDebtPaymentForm(forms.ModelForm):
    class Meta:
        model = ExpenseTransaction
        fields = ['name', 'amount', 'date']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(ExpenseTransactionDebtPaymentForm, self).__init__(*args, **kwargs)
