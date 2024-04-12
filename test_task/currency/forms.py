import datetime

from bootstrap_datepicker_plus.widgets import DatePickerInput
from dateutil.relativedelta import relativedelta
from django import forms
from django_select2 import forms as s2forms


class CountriesAndDatesSelectForm(forms.Form):
    countries = forms.MultipleChoiceField(label="Countries",
                                          widget=s2forms.Select2MultipleWidget(attrs={
                                              "data-allowClear": "true",
                                              "data-theme": "bootstrap-5",
                                              # "data-close-on-select": "false"
                                          }))
    start_date = forms.DateField(widget=DatePickerInput())#options={
    #                                                       'maxDate': (datetime.date.today()
    #                                                                   - relativedelta(days=1)).strftime('%Y-%m-%d')
    #                                                   }))
    end_date = forms.DateField(widget=DatePickerInput(range_from="start_date"))#,
                                                      # options={
                                                      #     'maxDate': datetime.date.today().strftime('%Y-%m-%d'),
                                                      # }))

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if end_date > start_date + relativedelta(years=2):
            self._errors['end_date'] = self.error_class([
                "Only 2 years range available"])

