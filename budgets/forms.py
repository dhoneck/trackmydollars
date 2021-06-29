from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import BudgetPeriod
from datetime import datetime

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ("email",)


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


# class BudgetPeriodForm(forms.ModelForm):
#     class Meta:
#         model = BudgetPeriod
#         fields = ['month, year']
#
    # def __init__(self, *args, **kwargs):
    #     print('KWARGS:', kwargs)
    #     print('ARGS:', args)
    #     self.user = kwargs.pop('user')
    #     print('USER IN FORM:', self.user)
    #     super(BudgetPeriodForm, self).__init__(*args, **kwargs)
    #     self.fields['template'] = forms.ModelChoiceField(required=False, queryset=BudgetPeriod.objects.filter(user_id=self.user).order_by('-month', '-year'))
        # self.fields['test'] = forms.ChoiceField(BudgetPeriod.objects.filter(user_id=self.user))
        # super(BudgetForm, self).__init__(*args, **kwargs)
        # print('IN BUDGETFORM!')
        # self.request = kwargs.pop('request', None)
        # print(self.request)
        # self.fields['template_budget'] = forms.ChoiceField(
        #     choices=[(str(0), str(o)) for o in BudgetPeriod.objects.filter(user=user)]
        # )

    # name = forms.CharField()
    # message = forms.CharField(widget=forms.Textarea)
    # user_id = forms.IntegerField()
    # month = forms.ChoiceField(choices=CHOICES)
    # year = forms.IntegerField()
    # starting_bank_balance = forms.DecimalField()
    # template_budget = forms.ModelMultipleChoiceField()
    # import_schedule_items = forms.BooleanField()

    # add_money_schedule_items = forms.BooleanField(default=False)
    # template_budget = forms.ForeignKey('self', on_delete=forms.CASCADE, null=True, blank=True)
    # pass




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
        # self.fields['test'] = forms.ChoiceField(BudgetPeriod.objects.filter(user_id=self.user))
        # super(BudgetForm, self).__init__(*args, **kwargs)
        # print('IN BUDGETFORM!')
        # self.request = kwargs.pop('request', None)
        # print(self.request)
        # self.fields['template_budget'] = forms.ChoiceField(
        #     choices=[(str(0), str(o)) for o in BudgetPeriod.objects.filter(user=user)]
        # )