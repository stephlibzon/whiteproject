 # Custom widgets / Complex controls required
from django.forms import Textarea, Widget, MultiWidget
from django.forms import widgets
import logging
logger = logging.getLogger("registry_log")


class BadCustomFieldWidget(Textarea):
    """
    Widget to use instead if a custom widget is defined and fails on creation
    """
    pass


class CustomWidgetC18583(Widget):
    def render(self, name, value, attrs=None):
        return "<h1>%s</h1>" % value


class DatatypeWidgetAlphanumericxxx(Textarea):
    def render(self, name, value, attrs=None):
        html = super(DatatypeWidgetAlphanumericxxx, self).render(name, value, attrs)
        return "<table border=3>%s</table>" % html


class OtherPleaseSpecifyWidget(MultiWidget):
    def __init__(self, main_choices, other_please_specify_value, unset_value, attrs=None):
        self.main_choices = main_choices
        self.other_please_specify_value = other_please_specify_value
        self.unset_value = unset_value

        _widgets = (
            widgets.Select(attrs=attrs, choices=self.main_choices),
            widgets.TextInput(attrs=attrs)
        )

        super(OtherPleaseSpecifyWidget, self).__init__(_widgets, attrs)

    def format_output(self, rendered_widgets):
        output = u'<BR>'.join(rendered_widgets)
        return output

    def decompress(self, value):
        """
        :param value: value from db or None
        :return: values to be supplied to the select widget and text widget:
        If no value, we show unset for dropdown and nothing in text
        If a value is supplied outside of the dropdown range we provide it to the text box
        and set the select widget to the indicator for "Other please specify"
        otherwise we provide the selected value to the select box and an empty string to
        the textbox
        """
        if not value:
            return [self.unset_value, ""]

        if value not in [choice[0] for choice in self.main_choices]:
            return [self.other_please_specify_value, value]
        else:
            return [value, ""]

    def value_from_datadict(self, data, files, name):
        logger.debug("value from datadict: data = %s name = %s" % (data, name))
        if name in data:
            return data[name]
        else:
            option_selected = data[name + "_0"]
            text_entered = data[name + "_1"]
            if option_selected == self.other_please_specify_value:
                return text_entered
            else:
                return option_selected

    def render(self, name, value, attrs=None):
        select_id = "id_" + name + "_0"
        specified_value_textbox_id = "id_" + name + "_1"
        script = """
        <script>
            (function() {
                $("#%s").bind("change", function() {
                    if ($(this).val() == "%s") {
                        $("#%s").show();
                    }
                    else {
                        $("#%s").hide();
                    }
                });
            })();
            (function(){ $("#%s").change();})();

        </script>
        """ % (select_id, self.other_please_specify_value, specified_value_textbox_id, specified_value_textbox_id, select_id)

        return super(OtherPleaseSpecifyWidget, self).render(name, value, attrs) + script