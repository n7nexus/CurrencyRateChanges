import json
import sqlite3
from datetime import date

import pandas as pd
from django.shortcuts import render
from django.views.generic import View

from .forms import CountriesAndDatesSelectForm


# Create your views here.
class CurrencyChangesView(View):
    allowed_currency_codes = ['USD', 'EUR', 'GPB', 'JPY', 'TRY', 'INR', 'CNY']

    finmarket_codes = dict(USD='52148', EUR='52170', GPB='52146', JPY='52246', TRY='52158', INR='52238', CNY='52207')

    iban_url = 'http://www.iban.ru/currency-codes'
    finmarket_url = 'https://www.finmarket.ru/currency/rates/'
    iban = pd.read_html(iban_url, thousands=None)

    countries_and_codes_df = iban[0].query('Код in @allowed_currency_codes')
    allowed_countries = countries_and_codes_df["Страна"].values.flatten().tolist()

    countries_choice_list = [
        (str(k), v)
        for k, v in enumerate(allowed_countries)
    ]

    initial_date = date.today()
    con = sqlite3.connect("db.sqlite3")
    try:
        print("Trying to get initial date")
        df = pd.read_sql_query("SELECT * FROM parameters", con)
        df['initial_date'] = pd.to_datetime(df['initial_date'])
        initial_date = df['initial_date'][0]
        print(initial_date)
    except:
        print('Initialize parameters table')
        df = pd.DataFrame({'initial_date': [initial_date]})
        df['initial_date'] = pd.to_datetime(df['initial_date'])
        df.to_sql(name="parameters", con=con, index=False)
    finally:
        con.close()

    def get(self, request, *args, **kwargs):

        form = CountriesAndDatesSelectForm()
        form.fields["countries"].choices = self.countries_choice_list
        context = {'form': form, 'currency_changes': json.dumps([])}
        return render(request, 'pages/home.html', context)

    def post(self, request, *args, **kwargs):
        form = CountriesAndDatesSelectForm(request.POST)
        form.fields["countries"].choices = self.countries_choice_list
        currency_changes = []
        if form.is_valid():
            form_data = form.cleaned_data
            start_date = form_data.get('start_date')
            end_date = form_data.get('end_date')
            countries = form_data.get('countries')

            print("debug: ", start_date, end_date)

            selected_countries = [c[1] for c in self.countries_choice_list if c[0] in countries]
            currencies_to_get = self.countries_and_codes_df.query('Страна in @selected_countries')[
                'Код'].drop_duplicates().values.flatten().tolist()

            data = pd.DataFrame()
            for currency in currencies_to_get:
                finmarket = self.getFinmarketTables(currency, end_date, start_date)
                currency_rates = self.prepareFinmarketTable(currency, finmarket)

                initial_currency_rate = self.getCurrencyRateForInitialDate(currency)

                print(data.head())

                # cur_ratio = (currency_rates['currency_rate'] - currency_rates['currency_rate'][0]) / \
                #             currency_rates['currency_rate'][0]
                cur_ratio = (currency_rates['currency_rate'] - initial_currency_rate) / \
                            initial_currency_rate
                currency_changes.append((currency, (currency_rates['date'].dt.strftime('%Y-%m-%d')).values.flatten().tolist(),
                                         cur_ratio.values.flatten().tolist()))

                data = pd.concat([data, currency_rates])

            self.mergeData(data)

        return render(request, 'pages/home.html', {'form': form, 'currency_changes': json.dumps(currency_changes)})

    def getFinmarketTables(self, currency, end_date: date, start_date: date):
        currency_code = self.finmarket_codes[currency]
        query_params = self.setFinmarketUrlQueryParams(currency_code, start_date, end_date)

        print("url = ", self.finmarket_url + query_params)
        finmarket = pd.read_html(self.finmarket_url + query_params, encoding="windows-1251", decimal=",",
                                 thousands=None)
        return finmarket

    def setFinmarketUrlQueryParams(self, currency_code, start_date: date, end_date: date):
        finmarket_url_query_params = '?id=10148&pv=1&cur={finmarket_code}&bd={s_day}&bm={s_month}&by={s_year}&ed={e_day}&em={e_month}&ey={e_year}'

        query_params = finmarket_url_query_params.format(finmarket_code=currency_code,
                                                         s_day=start_date.day, s_month=start_date.month,
                                                         s_year=start_date.year,
                                                         e_day=end_date.day, e_month=end_date.month,
                                                         e_year=end_date.year)
        return query_params

    def prepareFinmarketTable(self, currency, finmarket):
        currency_rates = finmarket[1]
        currency_rates.rename(columns={'Дата': 'date', 'Курс': 'currency_rate'}, inplace=True)
        currency_rates['date'] = pd.to_datetime(currency_rates['date'], dayfirst=True)
        currency_rates.drop(columns=['Кол-во', 'Изменение'], inplace=True)
        currency_rates["currency"] = currency
        return currency_rates

    def mergeData(self, data: pd.DataFrame):
        con = sqlite3.connect("db.sqlite3")
        try:
            print("Trying to get stored data")
            df = pd.read_sql_query("SELECT * FROM currency_rates", con)

            new_entries = pd.concat([data, df, df]).drop_duplicates(keep=False)
            if new_entries is not None:
                print("There are changes to store!!!")
                print(new_entries.head())
                new_entries['date'] = pd.to_datetime(new_entries['date'], dayfirst=True)

                new_entries.to_sql(name="currency_rates", con=con, index=False, if_exists="append")
        except:
            print("No stored data, initialaze with received values")
            print('Initialize parameters table')
            data.to_sql(name="currency_rates", con=con, index=False)
        finally:
            con.close()

    def getCurrencyRateForInitialDate(self, currency):
        con = sqlite3.connect("db.sqlite3")
        try:
            print("Trying to get stored initial currency rate")
            df = pd.read_sql_query("SELECT * FROM currency_rates", con)

            initial_date_df = df.query('currency = @currency and date = @self.initial_date')

            if initial_date_df.empty:
                finmarket = self.getFinmarketTables(currency, self.initial_date, self.initial_date)
                currency_rates = self.prepareFinmarketTable(currency, finmarket)

                new_entries = pd.concat([currency_rates, df, df]).drop_duplicates(keep=False)
                new_entries.to_sql(name="currency_rates", con=con, index=False, if_exists="append")
                return currency_rates['currency_rate'][0]
            else:
                return initial_date_df['currency_rate'][0]
        except:
            finmarket = self.getFinmarketTables(currency, self.initial_date, self.initial_date)
            currency_rates = self.prepareFinmarketTable(currency, finmarket)
            currency_rates.to_sql(name="currency_rates", con=con, index=False, if_exists="append")
            return currency_rates['currency_rate'][0]
        finally:
            con.close()
