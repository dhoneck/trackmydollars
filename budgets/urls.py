from django.conf.urls import include, url
from django.urls import path

from budgets.views import *
from . import views

urlpatterns = [
    # General URLs
    path('', views.index, name='index'),
    # path('about/', views.about, name='about'),
    # path('contact/', views.contact, name='contact'),
    # Registration and User URLs
    url(r'^accounts/', include('django.contrib.auth.urls')),
    url(r'^register/', views.register, name='register'),
    path('settings', EditSettings.as_view(), name='settings'),
    # Dashboard URLs
    path('dashboard/', views.dashboard, name='dashboard'),
    # Asset & Debt URLs
    path('assets-debts/', views.assets_debts, name='assets_debts'),
    path('assets-debts/add-asset', AddAsset.as_view(), name='add-asset'),
    path('assets-debts/add-installment-debt', AddInstallmentDebt.as_view(), name='add-installment-debt'),
    path('assets-debts/add-revolving-debt', AddRevolvingDebt.as_view(), name='add-revolving-debt'),
    path('assets-debts/assets/<int:id>/view/', views.view_asset_details),
    path('assets-debts/assets/<int:id>/update/', UpdateAsset.as_view()),
    path('assets-debts/assets/<int:id>/delete/', DeleteAsset.as_view()),
    path('assets-debts/assets/<int:id>/add-balance/', AddAssetBalance.as_view()),
    path('assets-debts/assets/<int:id>/update-balance/<int:bid>', UpdateAssetBalance.as_view()),
    path('assets-debts/assets/<int:id>/delete-balance/<int:bid>', DeleteAssetBalance.as_view()),
    path('assets-debts/installment-debts/<int:id>/view/', views.view_installment_debt_details),
    path('assets-debts/installment-debts/<int:id>/update/', UpdateInstallmentDebt.as_view()),
    path('assets-debts/installment-debts/<int:id>/delete/', DeleteInstallmentDebt.as_view()),
    path('assets-debts/installment-debts/<int:id>/add-balance/', AddInstallmentDebtBalance.as_view()),
    path('assets-debts/installment-debts/<int:id>/update-balance/<int:bid>', UpdateInstallmentDebtBalance.as_view()),
    path('assets-debts/installment-debts/<int:id>/delete-balance/<int:bid>', DeleteInstallmentDebtBalance.as_view()),
    path('assets-debts/revolving-debts/<int:id>/view/', views.view_revolving_debt_details),
    path('assets-debts/revolving-debts/<int:id>/update/', UpdateRevolvingDebt.as_view()),
    path('assets-debts/revolving-debts/<int:id>/delete/', DeleteRevolvingDebt.as_view()),
    path('assets-debts/revolving-debts/<int:id>/add-balance/', AddRevolvingDebtBalance.as_view()),
    path('assets-debts/revolving-debts/<int:id>/update-balance/<int:bid>', UpdateRevolvingDebtBalance.as_view()),
    path('assets-debts/revolving-debts/<int:id>/delete-balance/<int:bid>', DeleteRevolvingDebtBalance.as_view()),
    # Money Schedule URLs
    path('money-schedule/', views.view_schedule, name='money_schedule'),
    path('money-schedule/calculate', views.calculate_expense_fund, name='calculate_expense_fund'),
    path('money-schedule/add-schedule-item', AddScheduleItem.as_view(), name='add-money-schedule-item'),
    path('money-schedule/schedule-item/<siid>/update', UpdateScheduleItem.as_view()),
    path('money-schedule/schedule-item/<siid>/delete', DeleteScheduleItem.as_view()),
    # General Budget URLs
    path('budget/', views.budget, name='budget'),
    path('budget/<month>/<int:year>/', views.specific_budget),
    path('budget/<month>/<int:year>/add-budget/', AddBudgetPeriod.as_view()),
    path('budget/<month>/<int:year>/pay-debt/', AddDebtPayment.as_view()),
    path('budget/<month>/<int:year>/delete-budget/<int:id>', DeleteBudget.as_view()),
    path('budget/<month>/<int:year>/next', views.change_budget),
    path('budget/<month>/<int:year>/previous', views.change_budget),
    # Budget Income URLS
    path('budget/<month>/<int:year>/add-income-budget-item', AddIncomeBudgetItem.as_view()),
    path('budget/<month>/<int:year>/income-budget-item/<int:ibiid>/update', UpdateIncomeBudgetItem.as_view()),
    path('budget/<month>/<int:year>/income-budget-item/<int:ibiid>/delete', DeleteIncomeBudgetItem.as_view()),
    path('budget/<month>/<int:year>/income-budget-item/<int:ibiid>/view', views.view_income_budget_item),
    path('budget/<month>/<int:year>/income-budget-item/<int:ibiid>/add-income-transaction', AddIncomeTransaction.as_view()),
    path('budget/<month>/<int:year>/income-budget-item/<int:ibiid>/income-transaction/<int:itid>/update', UpdateIncomeTransaction.as_view()),
    path('budget/<month>/<int:year>/income-budget-item/<int:ibiid>/income-transaction/<int:itid>/delete', DeleteIncomeTransaction.as_view()),
    # Budget Expense URLs
    path('budget/<month>/<int:year>/update-budget-period/<int:bp>', UpdateBudgetPeriod.as_view()),
    path('budget/<month>/<int:year>/add-expense-category', AddExpenseCategory.as_view()),
    path('budget/<month>/<int:year>/expense-category/<int:ecid>/update', UpdateExpenseCategory.as_view()),
    path('budget/<month>/<int:year>/expense-category/<int:ecid>/delete', DeleteExpenseCategory.as_view()),
    path('budget/<month>/<int:year>/expense-category/<int:ecid>/add-expense-budget-item', AddExpenseBudgetItem.as_view()),
    path('budget/<month>/<int:year>/expense-category/<int:ecid>/expense-budget-item/<int:ebiid>/update', UpdateExpenseBudgetItem.as_view()),
    path('budget/<month>/<int:year>/expense-category/<int:ecid>/expense-budget-item/<int:ebiid>/delete', DeleteExpenseBudgetItem.as_view()),
    path('budget/<month>/<int:year>/expense-category/<int:ecid>/expense-budget-item/<int:ebiid>/view', views.view_expense_budget_item),
    path('budget/<month>/<int:year>/expense-category/<int:ecid>/expense-budget-item/<int:etiid>/add-expense-transaction', AddExpenseTransaction.as_view()),
    path('budget/<month>/<int:year>/expense-category/<int:ecid>/expense-budget-item/<int:etiid>/expense-transaction/<int:etid>/update', UpdateExpenseTransaction.as_view()),
    path('budget/<month>/<int:year>/expense-category/<int:ecid>/expense-budget-item/<int:etiid>/expense-transaction/<int:etid>/delete', DeleteExpenseTransaction.as_view()),
    # Reports URLs
    path('reports/', views.view_reports, name='reports'),
    # Offers URLS
    path('offers/', views.view_offers, name='offers'),
    # Support URLS
    path('contact/', AddContactEntry.as_view(), name='contact'),
]
