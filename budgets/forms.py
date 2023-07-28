from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import BudgetPeriod, ExpenseTransaction

WEBSITE_SECTIONS = (
    ('dashboard', 'Dashboard'),
    ('assets & debts', 'Assets & Debts'),
    ('money schedule', 'Money Schedule'),
    ('budget', 'Budget'),
    ('reports', 'Reports'),
    ('offers', 'Offers'),
    ('support', 'Support'),
)


class RegisterForm(UserCreationForm):
    email = forms.EmailField(max_length=200, help_text='Required')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class BudgetPeriodForm(forms.Form):
    starting_bank_balance = forms.DecimalField(max_digits=9, decimal_places=2, required=True)
    usable_bank_balance = forms.DecimalField(max_digits=9, decimal_places=2, required=True)
    starting_cash_balance = forms.DecimalField(max_digits=9, decimal_places=2, required=True)
    usable_cash_balance = forms.DecimalField(max_digits=9, decimal_places=2, required=True)
    add_money_schedule_items = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        money_schedule_items = kwargs.pop('money_schedule_items')
        print('money_schedule_items: ' + money_schedule_items)
        super(BudgetPeriodForm, self).__init__(*args, **kwargs)
        print(self.fields)
        self.fields['add_money_schedule_items'] = forms.BooleanField(required=False, label_suffix=f' ({money_schedule_items}):')
        self.fields['template'] = forms.ModelChoiceField(required=False, queryset=BudgetPeriod.objects.filter(user_id=self.user).order_by('-month', '-year'))


class DateForm(forms.Form):
    date = forms.DateTimeField(input_formats=['%Y-%m-%d'])


class ExpenseTransactionForm(forms.ModelForm):
    class Meta:
        model = ExpenseTransaction
        exclude = ['expense_budget_item', 'user', 'credit_payoff']

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


class SettingsForm(forms.Form):
    first_name = forms.CharField()
    last_name = forms.CharField()
    hide_sections = forms.MultipleChoiceField(
        choices=WEBSITE_SECTIONS,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'settings'})
    )
