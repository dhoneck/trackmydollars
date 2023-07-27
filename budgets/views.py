import datetime
import math
from functools import partial

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import IntegrityError
from django.http import Http404
from django.http import HttpResponseRedirect, HttpResponseNotFound
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView

from budgets.forms import *
from .models import *

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from .forms import SignupForm
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from .tokens import account_activation_token
from django.contrib.auth.models import User
from django.core.mail import EmailMessage

# TODO: Add a template budget page and functionality
# TODO: Figure out old and new debt in budget
# TODO: Add message script to each page - sometimes the message won't pop up until you go to a certain page
# TODO: Fix table formatting - column spacing, alignment, currency
# TODO: Fix the errors when importing templates and money schedule items
# TODO: Should integrity error apply on cap differences - eg Shopping vs shopping


# General Views
def index(request):
    """ Redirects user to login screen or dashboard based on current authentication status """
    if request.user.is_authenticated:
        return redirect('dashboard')
    else:
        return redirect('accounts/login/')


def about(request):
    """ An about page describing the service """
    return render(request, 'standard/view_about.html', )


def contact(request):
    """ A contact page for customer support or other feedback """
    return render(request, 'standard/view_contact.html', )


# Registration Views
def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            current_site = get_current_site(request)
            mail_subject = 'Activate your blog account.'
            context = {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            }
            print('user: ', context['user'])
            print('domain: ', context['domain'])
            print('uid: ', context['uid'])
            print('token: ', context['token'])
            message = render_to_string('registration/acc_active_email.html', context)
            print('message: ', message)
            to_email = form.cleaned_data.get('email')
            print('to_email: ', to_email)
            email = EmailMessage(
                        mail_subject, message, to=[to_email]
            )
            email.send()
            return HttpResponse('Please confirm your email address to complete the registration')
    else:
        form = SignupForm()
    return render(request, 'registration/signup.html', {'form': form})


def activate(request, uidb64, token):
    print('In activate')
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        print('uid: ', uid)
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        # return redirect('home')
        return HttpResponse('Thank you for your email confirmation. Now you can login your account.')
    else:
        return HttpResponse('Activation link is invalid!')


# TODO: Get users to sign in by email
# TODO: Send email verification emails
# TODO: Allow users to reset password
def register(request):
    """ User registration page """
    print('REQUEST:', request)
    if request.method == "GET":
        return render(
            request, "registration/register.html",
            {"form": CustomUserCreationForm}
        )
    elif request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(reverse("dashboard"))
        else:
            messages.error(request, form.errors)
            return render(
                request, "registration/register.html",
                {"form": CustomUserCreationForm}
            )


# User settings views
# TODO: Add a user avatar next to their email
# TODO: Finish user settings page
# TODO: Allow user to disable pages
# TODO: Allow user to disable checking account tracking
# TODO: Transfer In Item Name (e.g. Extra Funds) - for when automatic transfers happen such as 
# TODO: Transfer Out Category Name (e.g. Everything Else) - for when automatic transfers happen such as 
# TODO: Transfer Out Item Name (e.g. Reserved Funds)
class EditSettings(LoginRequiredMixin, FormView, SuccessMessageMixin):
    template_name = 'user-settings/view_settings.html'
    form_class = SettingsForm
    success_url = '../'
    success_message = 'Settings successfully added!'


# Helper Functions
def format_numbers(**kwargs):
    """
    Formats strings to the correct amount of spaces based on longest number
    Parameters:

    Returns:
        dict {int}: A dictionary containing numbers formatted to the same amount of numbers.
    """
    # Get the length of the longest integral number
    max_integral_length = 0
    for value in kwargs.values():
        len_of_value = len(str(value).split('.')[0])
        if len_of_value > max_integral_length:
            max_integral_length = len_of_value

    # Calculate number of commas
    commas = 0
    if max_integral_length > 3:
        commas = max_integral_length//3

    # Add total length of formatted number
    full_length = max_integral_length + commas + 3

    # Format numbers based on longest length
    formatted_numbers = {}
    format_string = "$ {:" + str(full_length) + ",.2f}"
    for key, value in kwargs.items():
        formatted_numbers[key] = format_string.format(value)
    return formatted_numbers

def format_to_currency_str(num):
    """Formats a number in"""
    return '{:.2f}'.format(num)

def add_lists(x, y):
    return x + y


def subtract_lists(x, y):
    return float('{:.2f}'.format(x-y))


def get_last_12_months_labels(get_next_12=False):
    """Get a list of abbreviated month names and a list of tuples containing year and month as strings"""
    month_labels = []
    year_month_labels = []

    current_date = datetime.today()

    # If get_next_12 is set to True it will set the current_date value 11 months ahead
    if get_next_12:
        current_date = current_date + relativedelta(months=11)

    month = (current_date.strftime('%b %Y'))
    month_labels.append(month)

    year_month = (current_date.strftime('%Y'), current_date.strftime('%m').lstrip('0'))
    year_month_labels.append(year_month)

    for m in range(1, 12):
        adjusted_date = current_date+relativedelta(months=-m)
        if m == 11:  # Makes last month include the year as well
            month = adjusted_date.strftime('%b %Y')
        else:
            month = adjusted_date.strftime('%b')
        year_month = (adjusted_date.strftime('%Y'), adjusted_date.strftime('%m').lstrip('0'))
        month_labels.insert(0, month)
        year_month_labels.insert(0, year_month)

    return month_labels, year_month_labels


def get_last_12_months_data(year, month, obj, obj_bal, user):
    """Add up the balances for an object based on year and month"""
    total_for_month = Decimal(0.00)

    # Loop through all of the objects
    for a in obj.objects.filter(user=user):

        filter_args = {}
        if issubclass(obj, Asset):
            filter_args['asset__id'] = a.id
        elif issubclass(obj, RevolvingDebt) or issubclass(obj, InstallmentDebt):
            filter_args['debt__id'] = a.id

        filter_args['date__year'] = year
        filter_args['date__month'] = month

        bal = obj_bal.objects.filter(**filter_args).first()

        if bal is not None:
            total_for_month += bal.balance

        elif bal is None:  # Check for last balance entry
            # kwargs
            kwargs = {"date__lt": date(int(year), int(month), 1)}
            if issubclass(obj, Asset):
                kwargs['asset_id'] = a.id
            elif issubclass(obj, RevolvingDebt):
                kwargs['debt_id'] = a.id
            elif issubclass(obj, InstallmentDebt):
                kwargs['debt_id'] = a.id

            remaining_balance = obj_bal.objects.filter(**kwargs).first()
            if remaining_balance is not None:
                total_for_month += remaining_balance.balance

    return float(total_for_month)


# User Based Views
# TODO: Add content from your money schedule
# TODO: Add content from your budget
# TODO: Prevent future month assets and debt balances from showing up in current month
# TODO: Provide more options for viewing net worth (e.g. week, month, year, all time)
@login_required
def dashboard(request):
    """ Shows an overview of the user's account """
    # TODO: Fix rounding issues for the net worth line - I see it has a rounding issue with too many decimals
    # Sum Assets
    asset_total = Decimal(0.00)
    for a in Asset.objects.filter(user=request.user.id):
        if a.balances.first() is not None:
            asset_total += a.balances.first().balance

    # Sum Debts
    debt_total = Decimal(0.00)
    for d in InstallmentDebt.objects.filter(user=request.user.id):
        if d.balances.first() is not None:
            debt_total += d.balances.first().balance

    for d in RevolvingDebt.objects.filter(user=request.user.id):
        if d.balances.first() is not None:
            debt_total += d.balances.first().balance

    # Calculate Net Worth
    net_worth_total = asset_total - debt_total

    # Get a list of abbreviated month names and a list of tuples containing year and month as strings ex: ('2020', '3')
    month_labels, year_month_labels = get_last_12_months_labels()

    # Convert year_month_labels into years and months list
    years = [year[0] for year in year_month_labels]
    months = [year[1] for year in year_month_labels]

    # Get a list of balances for assets, revolving debts, and installment debts for the last 12 months
    asset_partial = partial(get_last_12_months_data, obj=Asset, obj_bal=AssetBalance, user=request.user.id)
    asset_data = list(map(asset_partial, years, months))
    rev_debts_partial = partial(
        get_last_12_months_data, obj=RevolvingDebt, obj_bal=RevolvingDebtBalance, user=request.user.id
    )
    rev_debts_data = list(map(rev_debts_partial, years, months))
    inst_debts_partial = partial(
        get_last_12_months_data, obj=InstallmentDebt, obj_bal=InstallmentDebtBalance, user=request.user.id
    )
    inst_debts_data = list(map(inst_debts_partial, years, months))

    debt_data = list(map(add_lists, rev_debts_data, inst_debts_data))
    net_worth_data = list(map(subtract_lists, asset_data, debt_data))
    debt_data_negative = [-d for d in debt_data]

    formatted_totals = format_numbers(asset_total=asset_total,
                                      debt_total=debt_total,
                                      net_worth_total=net_worth_total)

    return render(request,
                  'dashboard/view_dashboard.html',
                  {'asset_total': formatted_totals['asset_total'],
                   'debt_total': formatted_totals['debt_total'],
                   'net_worth_total': formatted_totals['net_worth_total'],
                   'labels': month_labels,
                   'asset_data': asset_data,
                   'debt_data': debt_data_negative,
                   'net_worth_data': net_worth_data,
                   }
                  )


# Asset Views
@login_required
def assets_debts(request):
    # TODO: Fix number alignment
    # TODO: Fix months to be abbreviated - e.g. March should be mar instead of March
    assets = Asset.objects.filter(user=request.user.id).order_by('name')
    installment_debts = InstallmentDebt.objects.filter(user=request.user.id).order_by('name')
    revolving_debts = RevolvingDebt.objects.filter(user=request.user.id).order_by('name')

    # Net Worth Stats
    asset_total = 0
    for a in assets:
        if a.balances.first() is not None:
            asset_total += float(a.balances.first())
    #
    debt_total = 0
    for d in installment_debts:
        if d.balances.first() is not None:
            debt_total += float(d.balances.first())

    for d in revolving_debts:
        if d.balances.first() is not None:
            debt_total += float(d.balances.first())

    net_worth_total = asset_total - debt_total

    formatted_totals = format_numbers(asset_total=asset_total,
                                      debt_total=debt_total,
                                      net_worth_total=net_worth_total)
    return render(request,
                  'assets-debts/view_assets_debts.html',
                  {'assets': assets,
                   'installment_debts': installment_debts,
                   'revolving_debts': revolving_debts,
                   'asset_total': formatted_totals['asset_total'],
                   'debt_total': formatted_totals['debt_total'],
                   'net_worth_total': formatted_totals['net_worth_total']}
                  )


class AddAsset(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    # https://stackoverflow.com/questions/21652073/django-how-to-set-a-hidden-field-on-a-generic-create-view
    model = Asset
    fields = ['name', 'type']
    template_name = 'assets-debts/add_asset.html'
    success_url = '../assets-debts'
    success_message = 'Asset successfully added!'

    def form_valid(self, form):
        try:
            form.instance.user = self.request.user
            return super(AddAsset, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance}.',
                ))

class UpdateAsset(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Asset
    fields = ['name', 'type']
    template_name = 'assets-debts/update_asset.html'
    success_url = '../view'
    pk_url_kwarg = 'id'
    success_message = 'Asset successfully updated!'

    def get_object(self):
        return get_object_or_404(Asset, id=self.kwargs['id'], user_id=self.request.user.id)

    def form_valid(self, form):
        try:
            return super(UpdateAsset, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance}.',
                )
            )

@login_required
def view_asset_details(request, id):
    context = {}
    try:
        context['asset'] = Asset.objects.get(id=id, user_id=request.user.id)
    except Asset.DoesNotExist:
        raise Http404
    return render(request, 'assets-debts/view_asset.html', context)


class DeleteAsset(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Asset
    template_name = 'assets-debts/delete_asset.html'
    success_url = '../../../'
    pk_url_kwarg = 'id'
    success_message = 'Asset successfully deleted!'

    def get_object(self):
        return get_object_or_404(Asset, id=self.kwargs['id'], user=self.request.user.id)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteAsset, self).delete(request, *args, **kwargs)


# TODO: Remove asset from the form and add it to the template
# TODO: Handle form when values are not unique
class AddAssetBalance(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = AssetBalance
    fields = ['balance', 'date']
    template_name = 'assets-debts/add_asset_balance.html'
    success_url = '../view'
    success_message = 'Asset balance successfully added!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset_id = int(self.request.get_full_path().split('/')[-3])
        asset_name = get_object_or_404(Asset, id=asset_id, user_id=self.request.user.id).name
        context['asset_name'] = asset_name
        return context

    def get_initial(self):
        return {'date': datetime.today().strftime("%Y-%m-%d")}

    def form_valid(self, form):
        try:
            form.instance.user = self.request.user
            form.instance.asset_id = int(self.request.get_full_path().split('/')[-3])
            return super(AddAssetBalance, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance.date}.',
                )
            )


class UpdateAssetBalance(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = AssetBalance
    fields = ['balance', 'date']
    template_name = 'assets-debts/update_asset_balance.html'
    success_url = '../view'
    pk_url_kwarg = 'bid'
    success_message = 'Asset balance successfully updated!'

    def get_object(self):
        return get_object_or_404(AssetBalance, id=self.kwargs['bid'], user_id=self.request.user.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset_id = int(self.request.get_full_path().split('/')[-3])
        asset_name = get_object_or_404(Asset, id=asset_id, user_id=self.request.user.id).name
        context['asset_name'] = asset_name
        return context

    def form_valid(self, form):
        try:
            return super(UpdateAssetBalance, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance.date}.',
                )
            )


class DeleteAssetBalance(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = AssetBalance
    template_name = 'assets-debts/delete_asset_balance.html'
    success_url = '../view'
    pk_url_kwarg = 'bid'
    success_message = 'Asset balance successfully deleted!'

    def get_object(self):
        return get_object_or_404(AssetBalance, id=self.kwargs['bid'], user_id=self.request.user.id)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteAssetBalance, self).delete(request, *args, **kwargs)


# Debt Views
class AddInstallmentDebt(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = InstallmentDebt
    fields = ['name', 'type', 'initial_amount', 'interest_rate', 'minimum_payment', 'payoff_date']
    template_name = 'assets-debts/add_installment_debt.html'
    success_url = '../assets-debts'
    success_message = 'Installment debt successfully added!'

    def form_valid(self, form):
        try:
            form.instance.user = self.request.user
            return super(AddInstallmentDebt, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance}.',
                ))


class AddRevolvingDebt(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = RevolvingDebt
    fields = ['name', 'type', 'interest_rate', 'credit_limit']
    template_name = 'assets-debts/add_revolving_debt.html'
    success_url = '../assets-debts'
    success_message = 'Revolving debt successfully added!'

    def form_valid(self, form):
        try:
            form.instance.user = self.request.user
            return super(AddRevolvingDebt, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance}.',
                )
            )


class AddRevolvingDebtBalance(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = RevolvingDebtBalance
    fields = ['balance', 'date']
    template_name = 'assets-debts/add_revolving_debt_balance.html'
    success_url = '../view'
    success_message = 'Debt balance successfully added!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        debt_id = int(self.request.get_full_path().split('/')[-3])
        debt_name = RevolvingDebt.objects.get(id=debt_id, user_id=self.request.user.id).name
        context['debt_name'] = debt_name
        return context

    def get_initial(self):
        return {'debt': self.request.get_full_path().split('/')[-3],
                'date': datetime.today().strftime("%Y-%m-%d"),
                }

    def form_valid(self, form):
        try:
            form.instance.user = self.request.user
            form.instance.debt_id = int(self.request.get_full_path().split('/')[-3])
            return super(AddRevolvingDebtBalance, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance.date}.',
                )
            )


class UpdateInstallmentDebt(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = InstallmentDebt
    fields = ['name', 'type', 'initial_amount', 'interest_rate', 'minimum_payment', 'payoff_date']
    template_name = 'assets-debts/update_installment_debt.html'
    success_url = '../view'
    pk_url_kwarg = 'id'
    success_message = 'Installment debt successfully updated!'

    def get_object(self):
        return get_object_or_404(InstallmentDebt, id=self.kwargs['id'], user_id=self.request.user.id)

    def form_valid(self, form):
        try:
            return super(UpdateInstallmentDebt, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance}.',
                )
            )


class DeleteInstallmentDebt(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = InstallmentDebt
    template_name = 'assets-debts/delete_installment_debt.html'
    success_url = '../../../'
    pk_url_kwarg = 'id'
    success_message = 'Installment debt successfully deleted!'

    def get_object(self):
        return get_object_or_404(InstallmentDebt, id=self.kwargs['id'], user_id=self.request.user.id)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteInstallmentDebt, self).delete(request, *args, **kwargs)


class UpdateRevolvingDebt(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = RevolvingDebt
    fields = ['name', 'type', 'interest_rate', 'credit_limit']
    template_name = 'assets-debts/update_revolving_debt.html'
    success_url = '../view'
    pk_url_kwarg = 'id'
    success_message = 'Revolving debt successfully updated!'

    def get_object(self):
        return get_object_or_404(RevolvingDebt, id=self.kwargs['id'], user_id=self.request.user.id)

    def form_valid(self, form):
        try:
            return super(UpdateRevolvingDebt, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance}.',
                )
            )


class DeleteRevolvingDebt(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = RevolvingDebt
    template_name = 'assets-debts/delete_revolving_debt.html'
    success_url = '../../../'
    pk_url_kwarg = 'id'
    success_message = 'Revolving debt successfully deleted!'

    def get_object(self):
        return get_object_or_404(RevolvingDebt, id=self.kwargs['id'], user_id=self.request.user.id)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteRevolvingDebt, self).delete(request, *args, **kwargs)


class AddInstallmentDebtBalance(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = InstallmentDebtBalance
    fields = ['balance', 'date']
    template_name = 'assets-debts/add_installment_debt_balance.html'
    success_url = '../view'
    success_message = 'Debt balance successfully added!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        debt_id = int(self.request.get_full_path().split('/')[-3])
        debt_name = InstallmentDebt.objects.get(id=debt_id, user_id=self.request.user.id).name
        context['debt_name'] = debt_name
        return context

    def get_initial(self):
        return {'debt': self.request.get_full_path().split('/')[-3],
                'date': datetime.today().strftime("%Y-%m-%d"),
                }

    def form_valid(self, form):
        try:
            form.instance.user = self.request.user
            form.instance.debt_id = int(self.request.get_full_path().split('/')[-3])
            return super(AddInstallmentDebtBalance, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance.date}.',
                )
            )


class UpdateInstallmentDebtBalance(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = InstallmentDebtBalance
    fields = ['balance', 'date']
    template_name = 'assets-debts/update_installment_debt_balance.html'
    success_url = '../view'
    pk_url_kwarg = 'bid'
    success_message = 'Debt balance successfully updated!'

    def get_object(self):
        return get_object_or_404(InstallmentDebtBalance, id=self.kwargs['bid'], user_id=self.request.user.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        debt_id = int(self.request.get_full_path().split('/')[-3])
        debt_name = InstallmentDebt.objects.get(id=debt_id).name
        context['debt_name'] = debt_name
        return context

    def form_valid(self, form):
        try:
            return super(UpdateInstallmentDebtBalance, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance.date}.',
                )
            )


class DeleteInstallmentDebtBalance(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = InstallmentDebtBalance
    template_name = 'assets-debts/delete_installment_debt_balance.html'
    success_url = '../view'
    pk_url_kwarg = 'bid'
    success_message = 'Debt balance successfully deleted!'

    def get_object(self):
        return get_object_or_404(InstallmentDebtBalance, id=self.kwargs['bid'], user_id=self.request.user.id)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteInstallmentDebtBalance, self).delete(request, *args, **kwargs)


class UpdateRevolvingDebtBalance(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = RevolvingDebtBalance
    fields = ['balance', 'date']
    template_name = 'assets-debts/update_revolving_debt_balance.html'
    success_url = '../view'
    pk_url_kwarg = 'bid'
    success_message = 'Debt balance successfully updated!'

    def get_object(self):
        return get_object_or_404(RevolvingDebtBalance, id=self.kwargs['bid'], user_id=self.request.user.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        debt_id = int(self.request.get_full_path().split('/')[-3])
        debt_name = RevolvingDebt.objects.get(id=debt_id).name
        context['debt_name'] = debt_name
        return context

    def form_valid(self, form):
        try:
            return super(UpdateRevolvingDebtBalance, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance.date}.',
                )
            )


class UpdateIncomeBudgetItem(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = IncomeBudgetItem
    fields = ['name', 'planned_amount', 'type']
    template_name = 'budget/update_income_budget_item.html'
    success_url = '../../'
    pk_url_kwarg = 'ibiid'
    success_message = 'Income budget item successfully updated!'

    def get_object(self):
        return get_object_or_404(IncomeBudgetItem, id=self.kwargs['ibiid'], user_id=self.request.user.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month, year = get_month_and_year_from_request(self.request)
        user = self.request.user
        context['budget_period'] = get_budget_period(user, month, year)
        return context

    def form_valid(self, form):
        try:
            month, year = get_month_and_year_from_request(self.request)
            user = self.request.user
            form.instance.budget_period = get_budget_period(user, month, year)
            form.instance.user = user
            return super(UpdateIncomeBudgetItem, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance}.',
                ))

class DeleteIncomeBudgetItem(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = IncomeBudgetItem
    template_name = 'budget/delete_income_budget_item.html'
    success_url = '../../'
    pk_url_kwarg = 'ibiid'
    success_message = 'Income budget item successfully deleted!'

    def get_object(self):
        return get_object_or_404(IncomeBudgetItem, id=self.kwargs['ibiid'], user_id=self.request.user.id)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteIncomeBudgetItem, self).delete(request, *args, **kwargs)


class UpdateIncomeTransaction(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = IncomeTransaction
    fields = ['name', 'amount', 'cash', 'date']
    template_name = 'budget/update_income_transaction.html'
    success_url = '../../view'
    pk_url_kwarg = 'itid'
    success_message = 'Income transaction successfully updated!'

    def get_object(self):
        return get_object_or_404(IncomeTransaction, id=self.kwargs['itid'], user_id=self.request.user.id)

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.budget_item_id = self.request.get_full_path().split('/')[-4]
        return super(UpdateIncomeTransaction, self).form_valid(form)


class DeleteIncomeTransaction(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = IncomeTransaction
    template_name = 'budget/delete_income_transaction.html'
    success_url = '../../view'
    pk_url_kwarg = 'itid'
    success_message = 'Income transaction successfully deleted!'

    def get_object(self):
        return get_object_or_404(IncomeTransaction, id=self.kwargs['itid'], user_id=self.request.user.id)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteIncomeTransaction, self).delete(request, *args, **kwargs)


class UpdateExpenseCategory(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = ExpenseCategory
    fields = ['name']
    template_name = 'budget/update_expense_category.html'
    success_url = '../../'
    pk_url_kwarg = 'ecid'
    success_message = 'Expense category successfully updated!'

    def get_object(self):
        return get_object_or_404(ExpenseCategory, id=self.kwargs['ecid'], user_id=self.request.user.id)

    def form_valid(self, form):
        try:
            return super(UpdateExpenseCategory, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance}.',
                ))


class DeleteExpenseCategory(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = ExpenseCategory
    template_name = 'budget/delete_expense_category.html'
    success_url = '../../'
    pk_url_kwarg = 'ecid'
    success_message = 'Expense category successfully deleted!'

    def get_object(self):
        return get_object_or_404(ExpenseCategory, id=self.kwargs['ecid'], user_id=self.request.user.id)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteExpenseCategory, self).delete(request, *args, **kwargs)


class UpdateExpenseBudgetItem(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = ExpenseBudgetItem
    fields = ['name', 'expense_category', 'planned_amount', 'type']
    template_name = 'budget/update_expense_budget_item.html'
    success_url = '../../../../'
    pk_url_kwarg = 'ebiid'
    success_message = 'Expense budget item successfully updated!'

    # TODO: URLs with several keys may not be verified such as the expense category ID - doesn't affect anything at this time though
    def get_object(self):
        return get_object_or_404(ExpenseBudgetItem, id=self.kwargs['ebiid'], user_id=self.request.user.id)

    def get_form(self, form_class=None):
        form = super().get_form(form_class=None)
        month, year = get_month_and_year_from_request(self.request)
        bp = get_budget_period(self.request.user, month, year)
        form.fields['expense_category'].queryset = ExpenseCategory.objects.filter(budget_period=bp)
        return form

    def form_valid(self, form):
        try:
            form.instance.user = self.request.user
            return super(UpdateExpenseBudgetItem, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance}.',
                ))


class DeleteExpenseBudgetItem(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = ExpenseBudgetItem
    template_name = 'budget/delete_expense_budget_item.html'
    success_url = '../../../../'
    pk_url_kwarg = 'ebiid'
    success_message = 'Expense budget item successfully deleted!'

    def get_object(self):
        return get_object_or_404(ExpenseBudgetItem, id=self.kwargs['ebiid'], user_id=self.request.user.id)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteExpenseBudgetItem, self).delete(request, *args, **kwargs)


class UpdateExpenseTransaction(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = ExpenseTransaction
    fields = ['name', 'amount', 'credit_purchase', 'cash', 'date']
    template_name = 'budget/update_expense_transaction.html'
    success_url = '../../view'
    pk_url_kwarg = 'etid'
    success_message = 'Expense transaction item successfully updated!'

    def get_object(self):
        return get_object_or_404(ExpenseTransaction, id=self.kwargs['etid'], user_id=self.request.user.id)

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        form.instance.expense_budget_item_id = self.request.get_full_path().split('/')[-4]
        return super(UpdateExpenseTransaction, self).form_valid(form)


class DeleteExpenseTransaction(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = ExpenseTransaction
    template_name = 'budget/delete_expense_transaction.html'
    success_url = '../../view'
    pk_url_kwarg = 'etid'
    success_message = 'Expense transaction item successfully deleted!'

    def get_object(self):
        return get_object_or_404(ExpenseTransaction, id=self.kwargs['etid'], user_id=self.request.user.id)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteExpenseTransaction, self).delete(request, *args, **kwargs)


class DeleteRevolvingDebtBalance(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = RevolvingDebtBalance
    template_name = 'assets-debts/delete_revolving_debt_balance.html'
    success_url = '../view'
    pk_url_kwarg = 'bid'
    success_message = 'Debt balance successfully deleted!'

    def get_object(self):
        return get_object_or_404(RevolvingDebtBalance, id=self.kwargs['bid'], user_id=self.request.user.id)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteRevolvingDebtBalance, self).delete(request, *args, **kwargs)


@login_required
def view_installment_debt_details(request, id):
    context = {}
    try:
        context['debt'] = InstallmentDebt.objects.get(id=id, user_id=request.user.id)
    except InstallmentDebt.DoesNotExist:
        raise Http404
    return render(request, 'assets-debts/view_installment_debt.html', context)


@login_required
def view_revolving_debt_details(request, id):
    context = {}
    try:
        context['debt'] = RevolvingDebt.objects.get(id=id, user_id=request.user.id)
    except RevolvingDebt.DoesNotExist:
        raise Http404
    return render(request, 'assets-debts/view_revolving_debt.html', context)


@login_required
def get_month_and_year_from_request(request):
    split_url = request.get_full_path().split('/')
    month = split_url[2]
    year = split_url[3]
    # TODO: Throw 404 if month is not valid - year already errors if not number because of URL mapping
    return month, year


# Add Budget Views
# Do not use @login_required as it will cause an error
def get_budget_period(user, month, year):
    month = str(month)  # Convert for testing
    bp = None

    try:
        if month.isalpha:  # Convert from alpha (e.g. july) to int (e.g. 7)
            datetime_object = datetime.strptime(month, '%B')
            month_by_num = datetime_object.month
        else:
            month_by_num = int(month)
        bp = BudgetPeriod.objects.get(user=user, month=month_by_num, year=year)
    except BudgetPeriod.DoesNotExist:
        raise BudgetPeriod.DoesNotExist
    except Exception as err:
        return HttpResponseNotFound(f"Page not found! Here is the error: {err} {type(err)}")
    return bp


@login_required
def budget(request):
    # Get current month and year to pass onto another view as a default
    current_month = datetime.today().strftime('%B').lower()
    current_year = datetime.today().year
    return HttpResponseRedirect(f'{current_month}/{current_year}')


# TODO: Fix duplicate budget period message
# TODO: Fix conflicts of template and monthly schedule
# TODO: Add clickable month and year
# TODO: Make the month and year unchangeable
class AddBudgetPeriod(LoginRequiredMixin, FormView, SuccessMessageMixin):
    template_name = 'budget/add_budget.html'
    form_class = BudgetPeriodForm
    success_url = '../'
    success_message = 'Budget successfully added!'

    def get_form_kwargs(self):
        # Get list of money schedule items and their totals
        month, year = get_month_and_year_from_request(self.request)
        print(f'DOES THIS WORK?: {month} {year}')
        month_number = datetime.strptime(month, "%B").month
        print(month_number)

        money_schedule_items = ''
        for item in ScheduleItem.objects.filter(user=self.request.user.id):
            print('ITEM: ' + str(item))
            match = item.monthly_occurrences(int(year), month_number)
            if match:
                money_schedule_items += item.name + ' $' + str(item.get_monthly_total(int(year), month_number)) + ', '

        # Remove trailing comma
        if money_schedule_items[-2:] == ', ':
            money_schedule_items = money_schedule_items[:-2]
        else:
            money_schedule_items = 'No Schedule Items This Month'

        # Set the user for the form based on the request
        kwargs = super(AddBudgetPeriod, self).get_form_kwargs()
        kwargs.update({
            'user': self.request.user.id,
            'money_schedule_items': money_schedule_items,
        })
        return kwargs

    def get_context_data(self, **kwargs):
        # Provide the month and year to the template
        context = super().get_context_data(**kwargs)
        split_url = self.request.get_full_path().split('/')
        month = split_url[-4]
        year = split_url[-3]
        context['month'] = month.capitalize()
        context['year'] = year
        return context

    def form_valid(self, form):
        current_user = self.request.user.id

        split_url = self.request.get_full_path().split('/')
        month = datetime.strptime(split_url[-4], '%B').month
        year = split_url[-3]

        form_sbb = form.cleaned_data['starting_bank_balance']
        form_scb = form.cleaned_data['starting_cash_balance']

        try:
            # Create a new budget period
            BudgetPeriod(year=year,
                         month=month,
                         starting_bank_balance=form_sbb,
                         starting_cash_balance=form_scb,
                         user_id=current_user)\
                .save()

            # Retrieve the new budget period
            new_bp = BudgetPeriod.objects.get(year=year, month=month, user_id=current_user)

            # Check to see if there is a template budget period - if there is add those items to current budget
            template_bp = form.cleaned_data['template']
            if template_bp:
                # Add income budget items to the new budget period
                ibi = IncomeBudgetItem.objects.filter(budget_period_id=template_bp)
                for item in ibi:
                    item.pk = None
                    item.budget_period_id = new_bp.id
                    # TODO: Figure out how to delete this print statement - expense budget items won't transfer without
                    # Possibly a sync issue
                    print('item')
                    print(item)
                    item.save()
                # Add expense categories and expense budget items to the new budget period
                ec = ExpenseCategory.objects.filter(budget_period_id=template_bp).exclude(name='New Debt')
                for category in ec:
                    budget_items = category.expense_budget_items.all()
                    print('Budget Items')
                    print(budget_items)
                    category.id = None
                    category.budget_period_id = new_bp.id
                    category.save()
                    print(category)
                    new_id = category.id

                    for i in budget_items:
                        i.id = None
                        i.expense_category_id = new_id
                        i.save()

            usable_bank_balance = form.cleaned_data['usable_bank_balance']
            if usable_bank_balance > 0:
                reserve_bi = IncomeBudgetItem(
                    name='Bank Reserve',
                    planned_amount=usable_bank_balance,
                    budget_period_id=new_bp.id,
                    user_id=current_user,
                    type='Reserve'
                )
                reserve_bi.save()

            usable_cash_balance = form.cleaned_data['usable_cash_balance']
            if usable_cash_balance > 0:
                reserve_bi = IncomeBudgetItem(
                    name='Cash Reserve',
                    planned_amount=usable_cash_balance,
                    budget_period_id=new_bp.id,
                    user_id=current_user,
                    type='Reserve'
                )
                reserve_bi.save()

            add_money_schedule_items = form.cleaned_data['add_money_schedule_items']

            # Check for current month's budget items
            items_for_month = []
            if add_money_schedule_items:
                # for item in ScheduleItem.objects.filter(user=self.request.user.id).exclude(frequency="Monthly"):
                for item in ScheduleItem.objects.filter(user=self.request.user.id):
                    match = item.monthly_occurrences(int(year), int(month))
                    if match:
                        items_for_month.append(item.monthly_occurrences(int(year), int(month)))

                # Add money schedule items to budget
                for item in items_for_month:
                    # Check if expense category already exists
                    expense_cat, cat_created = ExpenseCategory.objects.get_or_create(
                        user_id=current_user,
                        budget_period=new_bp,
                        name=item[0].category)

                    expense_item, item_created = ExpenseBudgetItem.objects.get_or_create(
                        expense_category=expense_cat,
                        name=item[0].name,
                        planned_amount=item[0].amount,
                        user_id=item[0].user_id,
                    )

        except IntegrityError:
            messages.error(self.request, f"Budget already exists for {month}, {year}.")
            return HttpResponseRedirect(self.request.get_full_path())
        except Exception as err:
            return HttpResponseNotFound(f"Page not found! Here is the error: {err} {type(err)}")
        return super(AddBudgetPeriod, self).form_valid(form)


class UpdateBudgetPeriod(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = BudgetPeriod
    fields = ['starting_bank_balance', 'starting_cash_balance']
    template_name = 'budget/update_budget_period.html'
    success_url = '../'
    pk_url_kwarg = 'bp'
    success_message = 'Budget period successfully updated!'

    def get_object(self):
        return get_object_or_404(BudgetPeriod, id=self.kwargs['bp'], user_id=self.request.user.id)


# TODO: Fix auto reserve - only shows cash reserves
# TODO: Add transaction splitting
# TODO: Add an add transaction button
# TODO: Add autofill
# TODO: Allow users to move categories and budget items
# TODO: Prevent users from being able to add reserve transactions - it should be automatically
# TODO: Prevent negative incomes
# TODO: Add the ability to move transactions to other budget items
# TODO: Add quick edits with Ajax
# TODO: Add expense fund calculator
# TODO: Add a notification of outstanding CC balances from previous month
# TODO: Fix forms when duplicate data is added (e.g. adding a budget template and adding money schedule items
# TODO: Show money schedule items when adding a new budget
# TODO: Add help tooltips for various items such as budget overview items
# TODO: Add the ability to add sinking funds for expense fund to your income
# TODO: Add the ability to adjust your reserve funds after initial budget period creation
# TODO: Fix the "Skipping Django collectstatic since the env var DISABLE_COLLECTSTATIC is set."
@login_required
def specific_budget(request, month, year):
    """ Shows a breakdown of monthly budget """
    try:
        bp = get_budget_period(user=request.user.id, month=month, year=year)

        total_planned_income = Decimal(0.00)
        total_planned_expenses = Decimal(0.00)
        total_actual_income = Decimal(0.00)
        total_actual_expenses = Decimal(0.00)
        total_bank_income = Decimal(0.00)
        total_bank_expenses = Decimal(0.00)
        total_cash_income = Decimal(0.00)
        total_cash_expenses = Decimal(0.00)
        total_new_debt = Decimal(0.00)
        total_paid_debt = Decimal(0.00)
        reserved_funds = Decimal(0.00)

        income_budget_items = bp.income_budget_items.all()

        all_transactions = []

        for item in income_budget_items:
            total_planned_income += item.planned_amount

            # Check if reserved funds
            if item.type == 'Reserve':
                total_actual_income += item.planned_amount
                reserved_funds += item.planned_amount

            # Total income transactions
            for t in item.income_transactions.all():
                total_actual_income += t.amount
                all_transactions.append(t)
                if t.cash:
                    total_cash_income += t.amount
                elif not t.cash:
                    total_bank_income += t.amount

        # Check the transactions for new debt and adjust if needed
        print('Transactions Filter Method')

        credit_expense_transactions = ExpenseTransaction.objects.filter(
            expense_budget_item__expense_category__budget_period=bp,
            credit_purchase=True
        )
        print(f'Sum {credit_expense_transactions.aggregate(Sum("amount"))}')
        cc_purchase_total = credit_expense_transactions.aggregate(Sum('amount'))['amount__sum'] or Decimal(0.00)

        new_debt_category = bp.expense_categories.filter(name='New Debt')
        print(f'New debt {new_debt_category}')

        if new_debt_category:
            print('New Debt Exists')
            new_debt_budget_item = new_debt_category[0].expense_budget_items.all()[0]

            if new_debt_budget_item.planned_amount == cc_purchase_total:
                print('Do nothing w/ new debt!')
            else:
                print('Modifying new debt!')
                new_debt_budget_item.planned_amount = cc_purchase_total
                if new_debt_budget_item.planned_amount == 0:
                    print('Planned amount is 0, remove New Debt')
                    new_debt_budget_item.expense_category.delete()
                else:
                    print('Planned amount is not 0, modify New Debt')
                    new_debt_budget_item.save()
        if not new_debt_category and cc_purchase_total:
            try:
                user = request.user
                expense_cat, cat_created = ExpenseCategory.objects.get_or_create(
                    user=user,
                    budget_period=bp,
                    name='New Debt')
                expense_bi, created = ExpenseBudgetItem.objects.get_or_create(
                    user=user,
                    expense_category=expense_cat,
                    name='New Debt',
                    planned_amount=cc_purchase_total,
                )
                expense_bi.planned_amount = cc_purchase_total
                expense_bi.save()
            except IntegrityError:
                print(f'Your data has not been saved.')

        # Sum the planned expenses
        old_debt_paid = Decimal(0.00)

        expense_categories = bp.expense_categories.all()

        for category in expense_categories:
            for expense_budget_item in category.expense_budget_items.all():
                if expense_budget_item.name != 'New Debt':
                    total_planned_expenses += expense_budget_item.planned_amount

                # Check if reserved funds
                if expense_budget_item.type == 'Reserve':
                    total_actual_expenses += expense_budget_item.planned_amount
                    reserved_funds -= expense_budget_item.planned_amount

                for t in expense_budget_item.expense_transactions.all():
                    # total_actual_expenses += t.amount
                    all_transactions.append(t)
                    if t.credit_purchase:
                        total_new_debt += t.amount
                    elif t.cash:
                        total_cash_expenses += t.amount
                        total_actual_expenses += t.amount
                    else:
                        total_bank_expenses += t.amount
                        total_actual_expenses += t.amount
                    if t.credit_payoff:
                        old_debt_paid += t.amount
                        total_paid_debt += t.amount

        # Add debt payment transactions to all_transactions
        try:
            new_debt = bp.expense_categories.get(name='New Debt')
        except ExpenseCategory.DoesNotExist:
            new_debt = None
        if new_debt:
            # Remove New Debt from queryset and re-add it to a list to add it to the end
            expense_categories = expense_categories.exclude(name='New Debt')
            expense_categories = list(expense_categories)
            expense_categories.append(bp.expense_categories.get(name='New Debt'))

        sorted_transactions = sorted(all_transactions, key=lambda x: x.date, reverse=True)

    except BudgetPeriod.DoesNotExist:
        return HttpResponseRedirect('add-budget/')
    except Exception as err:
        return HttpResponseNotFound(f"Page not found! Here is the error: {err} {type(err)}")

    left_to_plan = total_planned_income - total_planned_expenses
    left_to_spend = total_actual_income - total_actual_expenses
    total_remaining_debt = total_new_debt - total_paid_debt

    print('total_bank_income: ', total_bank_income)
    print('total_bank_expenses: ', total_bank_expenses)
    bank_balance_change = total_bank_income - total_bank_expenses
    current_bank_balance = bp.starting_bank_balance + bank_balance_change

    print('total_cash_income: ', total_cash_income)
    print('total_cash_expenses: ', total_cash_expenses)
    cash_balance_change = total_cash_income - total_cash_expenses
    current_cash_balance = bp.starting_cash_balance + cash_balance_change

    return render(request,
                  'budget/view_budget.html',
                  {
                   'month': month.capitalize(),
                   'year': year,
                   'income_budget_items': income_budget_items,
                   'expense_categories': expense_categories,
                   'new_debt': new_debt,
                   'total_planned_income': total_planned_income,
                   'total_planned_expenses': total_planned_expenses,
                   'total_actual_income': total_actual_income,
                   'total_actual_expenses': total_actual_expenses,
                   'total_new_debt': total_new_debt,
                   'total_paid_debt': total_paid_debt,
                   'total_remaining_debt': total_remaining_debt,
                   'left_to_plan': left_to_plan,
                   'left_to_spend': left_to_spend,
                   'bp_id': bp.id,
                   'all_transactions': sorted_transactions,
                   'starting_bank_balance': bp.starting_bank_balance,
                   'bank_balance_change': bank_balance_change,
                   'current_bank_balance': current_bank_balance,
                   'starting_cash_balance': bp.starting_cash_balance,
                   'cash_balance_change': cash_balance_change,
                   'current_cash_balance': current_cash_balance,
                  }
                  )


@login_required
def change_budget(request, month, year):
    month = datetime.strptime(month, '%B').month
    current_budget = datetime(day=1, month=month, year=year)

    split_url = request.get_full_path().split("/")
    if split_url[-1] == "next":
        adjusted_date = current_budget+relativedelta(months=+1)
    elif split_url[-1] == "previous":
        adjusted_date = current_budget+relativedelta(months=-1)

    adjusted_month = adjusted_date.strftime("%B")
    adjusted_year = adjusted_date.year

    return HttpResponseRedirect(f'../../{adjusted_month}/{adjusted_year}')


@login_required
def view_income_budget_item(request, month, year, ibiid):
    context = {}
    try:
        context['income_budget_item'] = IncomeBudgetItem.objects.get(id=ibiid, user_id=request.user.id)
    except IncomeBudgetItem.DoesNotExist:
        raise Http404
    return render(request, 'budget/view_income_budget_item.html', context)

@login_required
def view_expense_budget_item(request, month, year, ecid, ebiid):
    context = {}
    try:
        context['expense_budget_item'] = ExpenseBudgetItem.objects.get(id=ebiid, user_id=request.user.id)
    except ExpenseBudgetItem.DoesNotExist:
        raise Http404
    return render(request, 'budget/view_expense_budget_item.html', context)


class AddIncomeBudgetItem(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = IncomeBudgetItem
    fields = ['name', 'planned_amount', 'type']
    template_name = 'budget/add_income_budget_item.html'
    success_url = './'
    success_message = 'Income budget item successfully added!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month, year = get_month_and_year_from_request(self.request)
        user = self.request.user
        context['budget_period'] = get_budget_period(user, month, year)
        return context

    def form_valid(self, form):
        try:
            month, year = get_month_and_year_from_request(self.request)
            user = self.request.user
            form.instance.budget_period = get_budget_period(user, month, year)
            form.instance.user = user
            return super(AddIncomeBudgetItem, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance}.',
                ))


class AddIncomeTransaction(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = IncomeTransaction
    fields = ['name', 'amount', 'cash', 'date']
    template_name = 'budget/add_income_transaction.html'
    success_message = 'Income transaction successfully added!'

    def get_success_url(self):
        if 'back_to_item_view' in self.request.POST:
            return './view'
        else:
            return '../../'

    def get_initial(self):
        return {
                'date': datetime.today(),
                }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['income_budget_item'] = IncomeBudgetItem.objects.get(
                id=self.request.get_full_path().split('/')[-2],
                user_id=self.request.user.id,
            )
        except Exception as err:
            print('There was an error:', err)
            context['income_budget_item'] = None
        if self.request.META.get('HTTP_REFERER').split('/')[-1] == 'view':
            context['destination'] = 'back_to_item_view'
        else:
            context['destination'] = 'back_to_budget_view'
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.budget_item_id = self.request.get_full_path().split('/')[-2]
        return super(AddIncomeTransaction, self).form_valid(form)


class AddExpenseCategory(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = ExpenseCategory
    fields = ['name']
    template_name = 'budget/add_expense_category.html'
    success_url = './'
    success_message = 'Expense category successfully added!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month, year = get_month_and_year_from_request(self.request)
        user = self.request.user
        context['budget_period'] = get_budget_period(user, month, year)
        return context

    def form_valid(self, form):
        try:
            month, year = get_month_and_year_from_request(self.request)
            user = self.request.user
            form.instance.budget_period = get_budget_period(user, month, year)
            form.instance.user = user
            return super(AddExpenseCategory, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance}.',
                ))

# TODO: Look this over, success url may need to be modified
class AddExpenseTransaction(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    template_name = 'budget/add_expense_transaction.html'
    form_class = ExpenseTransactionForm
    success_url = '../../../../'
    success_message = 'Expense transaction successfully added!'

    def get_form_kwargs(self):
        kwargs = super(AddExpenseTransaction, self).get_form_kwargs()
        kwargs.update({'user': self.request.user.id})
        return kwargs

    def get_initial(self):
        # TODO: Make sure foreign key 'Budget Item' only shows that months items
        return {
                'date': datetime.today(),
                }

    def get_success_url(self):
        if 'back_to_item_view' in self.request.POST:
            return './view'
        else:
            return '../../../../'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['expense_budget_item'] = ExpenseBudgetItem.objects.get(
                id=self.request.get_full_path().split('/')[-2],
                user_id=self.request.user.id,
            )
        except Exception as err:
            print('There was an error:', err)
            context['expense_budget_item'] = None
        if self.request.META.get('HTTP_REFERER').split('/')[-1] == 'view':
            context['destination'] = 'back_to_item_view'
        else:
            context['destination'] = 'back_to_budget_view'
        return context

    def form_valid(self, form):
        user = self.request.user
        form.instance.user = user
        form.instance.expense_budget_item_id = self.request.get_full_path().split('/')[-2]

        # If transaction was a credit purchase, add item to new debt expense
        if form.cleaned_data['credit_purchase']:
            month, year = get_month_and_year_from_request(self.request)
            bp = get_budget_period(user, month, year)
            expense_cat, cat_created = ExpenseCategory.objects.get_or_create(
                user=user,
                budget_period=bp,
                name='New Debt')

            try:
                expense_bi, created = ExpenseBudgetItem.objects.get_or_create(
                    user=user,
                    expense_category=expense_cat,
                    name='New Debt',
                    defaults={'planned_amount': 0},
                )
                expense_bi.planned_amount += form.cleaned_data['amount']
                expense_bi.save()
            except IntegrityError:
                return self.render_to_response(
                    self.get_context_data(
                        form=form,
                        message=f'Your data has not been saved because'
                                f' there is already an entry for {form.instance.date}.',
                    )
                )
        return super(AddExpenseTransaction, self).form_valid(form)


class AddExpenseBudgetItem(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    # TODO: Only show expense categories in that budget period
    model = ExpenseBudgetItem
    fields = ['name', 'planned_amount', 'type']
    template_name = 'budget/add_expense_budget_item.html'
    success_url = '../../'
    success_message = 'Expense budget item successfully added!'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        expense_category_id = int(self.request.get_full_path().split('/')[-2])
        expense_category = get_object_or_404(ExpenseCategory, id=expense_category_id, user_id=self.request.user.id)
        context['expense_category'] = expense_category
        return context

    def form_valid(self, form):
        try:
            form.instance.user = self.request.user
            form.instance.expense_category_id = self.request.get_full_path().split('/')[-2]
            return super(AddExpenseBudgetItem, self).form_valid(form)
        except IntegrityError:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'Your data has not been saved because there is already an entry for {form.instance}.',
                ))

class DeleteBudget(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = BudgetPeriod
    template_name = 'budget/delete_budget.html'
    success_url = '/budget/'
    pk_url_kwarg = 'id'
    success_message = 'Budget successfully deleted!'

    def get_object(self):
        return get_object_or_404(BudgetPeriod, id=self.kwargs['id'], user_id=self.request.user.id)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteBudget, self).delete(request, *args, **kwargs)


class AddDebtPayment(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    template_name = 'budget/add_debt_payment.html'
    form_class = ExpenseTransactionDebtPaymentForm
    success_url = '../'
    success_message = 'Debt payment successfully added!'

    def get_form_kwargs(self):
        kwargs = super(AddDebtPayment, self).get_form_kwargs()
        kwargs.update({'user': self.request.user.id})
        return kwargs

    def get_initial(self):
        return {
            'date': datetime.today(),
        }

    def form_valid(self, form):
        try:
            month, year = get_month_and_year_from_request(self.request)
            user = self.request.user.id
            bp = get_budget_period(user, month, year)
            new_debt_bi = bp.expense_categories.get(name='New Debt').expense_budget_items.get(name='New Debt').id

            self.object = form.save(commit=False)
            self.object.user_id = user
            self.object.expense_budget_item_id = new_debt_bi
            self.object.credit_payoff = True
            self.object.save()

            return super(AddDebtPayment, self).form_valid(form)
        except Exception as e:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    message=f'There is an issue. Month or year may be wrong in URL.',
                )
            )

# Schedule Views
def get_items_by_frequency(request, frequency):
    """
    Get schedule items by frequency and user ID
    Parameters:
        request (django.core.handlers.wsgi.WSGIRequest): The current request
        frequency (str): The schedule item frequency

    Returns:
        django.db.models.query.QuerySet: Schedule items
    """
    return ScheduleItem\
        .objects\
        .filter(user=request.user.id, frequency=frequency)\
        .order_by('first_due_date__month', 'first_due_date__day')


def get_all_schedule_items(request):
    """
    Gets a dictionary of all the schedule items for a particular user.
    Parameters:
        request (django.core.handlers.wsgi.WSGIRequest): The current request

    Returns:
        dict: Contains frequency (str) and schedule items (QuerySet)
    """
    all_schedule_items = {
        'weekly': get_items_by_frequency(request, 'Weekly'),
        'every_two_weeks': get_items_by_frequency(request, 'Every two weeks'),
        'monthly': get_items_by_frequency(request, 'Monthly'),
        'every_two_months': get_items_by_frequency(request, 'Every two months'),
        'quarterly': get_items_by_frequency(request, 'Quarterly'),
        'every_six_months': get_items_by_frequency(request, 'Every six months'),
        'yearly': get_items_by_frequency(request, 'Yearly'),
        'one_time': get_items_by_frequency(request, 'One time only'),
    }
    return all_schedule_items

def get_all_schedule_totals(request):
    """
        Gets a dictionary of all the schedule item totals for a particular user.
        Parameters:
            request (django.core.handlers.wsgi.WSGIRequest): The current request

        Returns:
            dict
        """
    all_items = get_all_schedule_items(request)
    all_totals = {
        'weekly_total': (all_items['weekly'].aggregate(Sum('amount'))['amount__sum'] or 0) * 52,
        'every_two_weeks_total': (all_items['every_two_weeks'].aggregate(Sum('amount'))['amount__sum'] or 0) * 26,
        'monthly_total': (all_items['monthly'].aggregate(Sum('amount'))['amount__sum'] or 0) * 12,
        'every_two_months_total': (all_items['every_two_months'].aggregate(Sum('amount'))['amount__sum'] or 0) * 6,
        'quarterly_total': (all_items['quarterly'].aggregate(Sum('amount'))['amount__sum'] or 0) * 4,
        'every_six_months_total': (all_items['every_six_months'].aggregate(Sum('amount'))['amount__sum'] or 0) * 2,
        'yearly_total': (all_items['yearly'].aggregate(Sum('amount'))['amount__sum'] or 0) * 1,
        'one_time_total': (all_items['one_time'].aggregate(Sum('amount'))['amount__sum'] or 0) * 1,
    }
    return all_totals

@login_required
def view_schedule(request):
    # Grab all schedule items
    context = get_all_schedule_items(request)

    #  Grab all schedule item totals
    totals = get_all_schedule_totals(request)

    entire_total = Decimal(0.00)
    non_monthly_total = Decimal(0.00)

    # Get total of all items except 'monthly' items
    # TODO: Figure out how to handle weekly and every two weeks - add only the extra amounts to the non-monthly total?
    for key, value in totals.items():
        if key != 'monthly_total':
            non_monthly_total += value
        entire_total += value

    totals['entire_total'] = "{:.2f}".format(entire_total)
    totals['non_monthly_total'] = "{:.2f}".format(non_monthly_total)

    totals['non_monthly_per_month_total'] = Decimal("{:.2f}".format(non_monthly_total / 12))

    context['totals'] = totals
    print('Context')
    print(context)

    month_labels, year_month_tuple = get_last_12_months_labels(get_next_12=True)
    print(month_labels)
    print(year_month_tuple)

    # Separate the month from the year on the last element in the list and add them to separate variables
    month_labels[11], year = month_labels[11].split(' ')

    # Loop through months and add the year next to Jan
    for idx, month in enumerate(month_labels):
        if month == 'Jan':
            month_labels[idx] = 'Jan ' + year

    item_data = []

    # Loop through a year of year/month pairs
    idx = 0
    for year, month in year_month_tuple:
        # Loop through all schedule items
        month_total = Decimal(0.0)
        for item in ScheduleItem.objects.filter(user=request.user.id).exclude(frequency="Monthly"):
            month_total += item.get_monthly_total(int(year), int(month))
        item_data.append((month_labels[idx], "{:0.2f}".format(month_total)))
        idx += 1

    context['month_data'] = item_data

    # TODO: Fix month column to show the new year next to January
    # TODO: Fix alignment and formatting
    return render(request, 'money-schedule/view_schedule.html', context)


class AddScheduleItem(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = ScheduleItem
    fields = ['name', 'amount', 'category', 'type', 'first_due_date', 'frequency']
    template_name = 'money-schedule/add_schedule_item.html'
    success_url = '/money-schedule/'
    success_message = 'Schedule item successfully added!'

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(AddScheduleItem, self).form_valid(form)


class UpdateScheduleItem(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = ScheduleItem
    fields = ['name', 'amount', 'category', 'first_due_date', 'frequency']
    template_name = 'money-schedule/update_schedule_item.html'
    success_url = '/money-schedule/'
    pk_url_kwarg = 'siid'
    success_message = 'Schedule item successfully updated!'

    def get_object(self):
        return get_object_or_404(ScheduleItem, id=self.kwargs['siid'], user_id=self.request.user.id)


class DeleteScheduleItem(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    model = ScheduleItem
    template_name = 'money-schedule/delete_schedule_item.html'
    success_url = '/money-schedule/'
    pk_url_kwarg = 'siid'
    success_message = 'Schedule item successfully deleted!'

    def get_object(self):
        return get_object_or_404(ScheduleItem, id=self.kwargs['siid'], user_id=self.request.user.id)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(DeleteScheduleItem, self).delete(request, *args, **kwargs)


def get_active_items(request):
    """ Return only active schedule items for requested user """
    items = ScheduleItem.objects.filter(user_id=request.user.id)
    print(items)
    active_item_ids = [item.id for item in items if item.is_active() == True]
    active_items = items.filter(id__in=active_item_ids)
    return active_items


def calculate_expense_fund(request):
    """ A form to figure out how much to contribute to your emergency fund """

    # TODO: Figure out how to handle weekly and every two weeks - add only the extra amounts to the non-monthly total?
    # Get total of all items except 'monthly' items
    totals = get_all_schedule_totals(request)
    non_monthly_total = Decimal(0.00)
    for key, value in totals.items():
        entire_total = 0
        if key != 'monthly_total':
            non_monthly_total += value
        entire_total += value
    non_monthly_total = non_monthly_total;
    non_monthly_total_avg = non_monthly_total/12;
    suggestion = math.ceil(non_monthly_total_avg / 10) * 10

    next_12_months, year_month_tuples = get_last_12_months_labels(True)
    print('year_month_tuples')
    print(year_month_tuples)
    print(next_12_months)
    table_data = []
    last_month_balance = 0
    print('get_all_schedule_totals(request)')
    print(get_all_schedule_totals(request))
    for idx in range(12):
        print('idx:', idx)
        if idx == 0:
            fund_in = suggestion
        else:
            fund_in = suggestion

        # Get month and year based on index of loop
        current_month = year_month_tuples[idx][1]
        current_year = year_month_tuples[idx][0]

        # Loop through all objects
        print('Month/Year: ' + current_month + '/' + current_year)
        active_items = get_active_items(request)
        month_total = 0
        for item in active_items:
            # item.get_monthly_total(current_year, current_month)
            print(item.name, '-', item.get_monthly_total(current_year, current_month))
            month_total += item.get_monthly_total(current_year, current_month)
        print('Month Total: ' + str(month_total))
        fund_out = month_total
        current_month_balance = last_month_balance + fund_in - fund_out
        last_month_balance = current_month_balance
        month_data = {
            'month': next_12_months[idx],
            'fund_in': fund_in,
            'fund_out': fund_out,
            'fund_balance': current_month_balance,
        }
        table_data.append(month_data)

    print(table_data)

    # TODO: Add expenses that may happen outside of the next year to make sure they are accounted for
    active_items = get_active_items(request).exclude(frequency="Monthly");
    active_items = sorted(active_items, key=lambda a: a.get_next_payment())

    return render(
        request, "money-schedule/calculate_expense_fund.html",
        {
            "items": active_items,
            "suggestion": suggestion,
            "non_monthly_total": format_to_currency_str(non_monthly_total),
            "non_monthly_total_avg": format_to_currency_str(non_monthly_total_avg),
            "next_12_months": next_12_months,
            "table_data": table_data,
            "non_monthly_total": format_to_currency_str(non_monthly_total),
            "non_monthly_total_avg": format_to_currency_str(non_monthly_total_avg),
        }
    )


# Report Views
# TODO: Asset and debts reports
# TODO: Money schedule reports
# TODO: Budget reports
@login_required
def view_reports(request):
    return render(request, 'reports/reports.html')


# Offer Views
# TODO: Changing payment times to make sure you have money to pay bills between paychecks
# TODO: 1-month advance in your checking to give you cushion
# TODO: 3-6 months savings reserve
# TODO: Account balance is currently low
# TODO: Account balance will be too low to pay future expenses based on money cycle
# TODO: Upcoming expenses
@login_required
def view_offers(request):
    return render(request, 'offers/view_offers.html')


# Support Views
# TODO: Create support articles
class AddContactEntry(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = ContactEntry
    fields = ['reason_for_contact', 'description']
    template_name = 'support/add_contact_entry.html'
    success_url = './'
    success_message = 'Contact form successfully submitted!'

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(AddContactEntry, self).form_valid(form)
