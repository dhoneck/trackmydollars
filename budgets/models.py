from django.db import models

# import copy
# import calendar
from datetime import datetime

INCOME_OR_EXPENSE = (
    ('Income', 'Income'),
    ('Expense', 'Expense'),
)

FREQUENCY = (
    ('One time only', 'One time only'),
    ('Weekly', 'Weekly'),
    ('Every two weeks', 'Every two weeks'),
    ('Monthly', 'Monthly'),
    ('Every two months', 'Every two months'),
    ('Quarterly', 'Quarterly'),
    ('Every six months', 'Every six months'),
    ('Yearly', 'Yearly'),
)

MONTHS = (
    ('01', 'Jan'),
    ('02', 'Feb'),
    ('03', 'Mar'),
    ('04', 'Apr'),
    ('05', 'May'),
    ('06', 'Jun'),
    ('07', 'Jul'),
    ('08', 'Aug'),
    ('09', 'Sep'),
    ('10', 'Oct'),
    ('11', 'Nov'),
    ('12', 'Dec'),
)

NEED_WANT_SAVINGS_DEBT = (
    ('Need', 'Need'),
    ('Want', 'Want'),
    ('Savings & Debt', 'Savings & Debt'),
)


# Asset and Debt Models
class Asset(models.Model):
    name = models.CharField(max_length=50, unique=True)
    asset_type = models.CharField(max_length=50, blank=True)

    def __str__(self):
        if self.asset_type == '':
            return self.name
        else:
            return self.name + ' - ' + self.asset_type

    class Meta:
        ordering = ('name',)


class Debt(models.Model):
    name = models.CharField(max_length=50, unique=True)
    type = models.CharField(max_length=50, blank=True, default='')
    initial_balance = models.DecimalField(max_digits=11, decimal_places=2, blank=True, default=0.00)
    interest_rate = models.DecimalField(max_digits=9, decimal_places=4, blank=True, null=True)
    date_opened = models.DateField(blank=True, null=True)

    def __str__(self):
        if self.type == '':
            return self.name
        else:
            return self.name + ' - ' + self.type

    class Meta:
        ordering = ('name',)
        abstract = True


class InstallmentDebt(Debt):
    minimum_payment = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
    payoff_date = models.DateField(blank=True, null=True)


class RevolvingDebt(Debt):
    credit_limit = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)


class Balance(models.Model):
    balance = models.DecimalField(max_digits=9, decimal_places=2)
    date = models.DateField(blank=True, null=True)

    def __str__(self):
        return str(self.balance)

    def __float__(self):
        if self.balance is None:
            return 0.00
        else:
            return float(self.balance)

    class Meta:
        get_latest_by = 'date'
        abstract = True


class AssetBalance(Balance):
    asset = models.ForeignKey('Asset', on_delete=models.CASCADE, related_name='balances')

    class Meta:
        unique_together = ('asset', 'date',)
        ordering = ('-date', 'asset')


class InstallmentDebtBalance(Balance):
    debt = models.ForeignKey('InstallmentDebt', on_delete=models.CASCADE, related_name='balances')

    class Meta:
        unique_together = ('debt', 'date',)
        ordering = ('-date', 'debt')


class RevolvingDebtBalance(Balance):
    debt = models.ForeignKey('RevolvingDebt', on_delete=models.CASCADE, related_name='balances')

    class Meta:
        unique_together = ('debt', 'date',)
        ordering = ('-date', 'debt')


# Budget Models
class BudgetPeriod(models.Model):
    CHOICES = [(i, i) for i in range(1, 13)]
    # CHOICES = (
    #     (1, '01 - Jan'),
    #     (2, '02 - Feb'),
    #     (3, '03 - Mar'),
    #     (4, '04 - Apr'),
    #     (5, '05 - May'),
    #     (6, '06 - Jun'),
    #     (7, '07 - Jul'),
    #     (8, '08 - Aug'),
    #     (9, '09 - Sep'),
    #     (10, '10 - Oct'),
    #     (11, '11 - Nov'),
    #     (12, '12 - Dec'),
    # )
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
    month = models.IntegerField(choices=CHOICES, default=datetime.today().month)
    year = models.PositiveIntegerField(default=datetime.today().year)
    starting_revolving = models.DecimalField(max_digits=9, decimal_places=2, default=0, null=True)
    starting_checking = models.DecimalField(max_digits=9, decimal_places=2, default=0, null=True)

    class Meta:
        unique_together = ('month', 'year',)
        verbose_name_plural = 'Monthly budget info'

    def __str__(self):
        return str(self.year) + ' - ' + str(self.CHOICES[self.month-1][1])


class IncomeBudgetItem(models.Model):
    budget_period = models.ForeignKey('BudgetPeriod', on_delete=models.CASCADE, related_name='income_budget_items')
    name = models.CharField(max_length=50)
    planned_amount = models.DecimalField(max_digits=9, decimal_places=2)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('-planned_amount', 'name',)
        unique_together = ('budget_period', 'name',)


class IncomeTransaction(models.Model):
    # TODO: Add limited_choices_to in budget_item to prevent seeing other months items
    # https://stackoverflow.com/questions/31578559/django-foreignkey-limit-choices-to-a-different-foreignkey-id
    # https://stackoverflow.com/questions/7133455/django-limit-choices-to-doesnt-work-on-manytomanyfield
    budget_item = models.ForeignKey('IncomeBudgetItem',
                                    on_delete=models.CASCADE,
                                    related_name='income_transactions',
                                    # limit_choices_to={"budget_period_id": 2},
                                    )
    name = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    date = models.DateField()

    def __float__(self):
        if self.amount is None:
            return 0.00
        else:
            return float(self.amount)

    def __str__(self):
        return self.name + ' for ' + '$' + str(self.amount) + ' on ' + str(self.date)

    class Meta:
        ordering = ('-amount', 'name',)
        unique_together = ('budget_item', 'name',)


class ExpenseCategory(models.Model):
    budget_period = models.ForeignKey('BudgetPeriod', on_delete=models.CASCADE, related_name='expense_categories')
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name + ' for ' + str(self.budget_period)

    class Meta:
        verbose_name_plural = 'Expense categories'
        unique_together = ('name', 'budget_period')


class ExpenseBudgetItem(models.Model):
    expense_category = models.ForeignKey('ExpenseCategory', on_delete=models.CASCADE, related_name='expense_budget_items')
    name = models.CharField(max_length=50, unique=True)
    planned_amount = models.DecimalField(max_digits=9, decimal_places=2)
    # need_want_savings_debt = models.CharField(max_length=25, choices=NEED_WANT_SAVINGS_DEBT)

    def __str__(self):
        return self.name + ' for $' + str(self.planned_amount)

    def __float__(self):
        if self.amount is None:
            return 0.00
        else:
            return float(self.amount)

    class Meta:
        unique_together = ('name', 'expense_category')


class ExpenseTransaction(models.Model):
    expense_budget_item = models.ForeignKey('ExpenseBudgetItem', on_delete=models.CASCADE, related_name='expense_transactions')
    name = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    credit_purchase = models.BooleanField(default=False)
    date = models.DateField()
