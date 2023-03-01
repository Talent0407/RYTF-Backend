from django import forms

from .models import Collection


class CollectionAdminForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = "__all__"

    def clean(self, *args, **kwargs):
        super().clean()
        contract_address = self.cleaned_data["contract_address"]
        qs = Collection.objects.filter(contract_address=contract_address)
        if qs.exists():
            raise forms.ValidationError(
                "A collection with this contract address already exists"
            )
