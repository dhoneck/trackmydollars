from django.contrib import admin

from .models import *


class AssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'type')


class AssetBalanceAdmin(admin.ModelAdmin):
    list_display = ('asset', 'balance', 'date')


class BudgetPeriodAdmin(admin.ModelAdmin):
    list_display = ('user', 'year', 'month')


class InstallmentDebtAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'interest_rate',)


class InstallmentDebtBalanceAdmin(admin.ModelAdmin):
    list_display = ('debt', 'balance', 'date')


class RevolvingDebtAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'interest_rate', 'credit_limit',)


class RevolvingDebtBalanceAdmin(admin.ModelAdmin):
    list_display = ('debt', 'balance', 'date')


admin.site.register(Asset, AssetAdmin)
admin.site.register(AssetBalance, AssetBalanceAdmin)
admin.site.register(InstallmentDebt, InstallmentDebtAdmin)
admin.site.register(InstallmentDebtBalance, InstallmentDebtBalanceAdmin)
admin.site.register(RevolvingDebt, RevolvingDebtAdmin)
admin.site.register(RevolvingDebtBalance, RevolvingDebtBalanceAdmin)
admin.site.register(ScheduleItem)
admin.site.register(BudgetPeriod, BudgetPeriodAdmin)
admin.site.register(IncomeBudgetItem)
admin.site.register(IncomeTransaction)
admin.site.register(ExpenseCategory)
admin.site.register(ExpenseBudgetItem)
admin.site.register(ExpenseTransaction)
