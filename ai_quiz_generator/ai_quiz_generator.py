from xblock.fields import Float, Integer, Scope, String
from xblock.core import XBlock
from xblock.completable import CompletableXBlockMixin
from xblock.validation import ValidationMessage
from web_fragments.fragment import Fragment
from django.template import Context, Template
from django.conf import settings
import logging

from openai import OpenAI

try:
    from xblock.utils.studio_editable import StudioEditableXBlockMixin
except ModuleNotFoundError:
    from xblockutils.studio_editable import StudioEditableXBlockMixin

try:
    import importlib_resources
except ModuleNotFoundError:
    from importlib import resources as importlib_resources

log = logging.getLogger(__name__)
def _(text): return text


@XBlock.wants('i18n')
class AIQuizGeneratorXBlock(XBlock, StudioEditableXBlockMixin, CompletableXBlockMixin):
    """
    AI Quiz Generator XBlock - Generates multiple choice quiz questions using OpenAI models.
    """

    display_name = String(
        display_name=_('Display Name'),
        help=_('Display name for this module'),
        default="AI Quiz Generator",
        scope=Scope.settings
    )

    topic = String(
        display_name=_('Quiz Topic'),
        default='',
        scope=Scope.settings,
        multiline_editor=True,
        help=_('Enter the topic or concept you want to generate a quiz about.'),
    )

    generated_quiz = String(
        display_name=_('Generated Quiz'),
        default='',
        scope=Scope.user_state,
        help=_('Stores the generated quiz from AI.')
    )

    context = String(
        display_name=_('Prompt Template'),
        default="""
        Generate a multiple-choice question on the following topic:
        Topic: {{topic}}
        Format:
        Question:
        A.
        B.
        C.
        D.
        Correct Answer:
        """,
        scope=Scope.settings,
        multiline_editor=True,
        help=_("Prompt template with {{topic}} placeholder."),
    )

    api_key = String(
        display_name=_("API Key"),
        default=getattr(settings, 'OPENAI_SECRET_KEY', ''),
        scope=Scope.settings,
        help=_("Your OpenAI API key.")
    )

    model_name = String(
        display_name=_("AI Model Name"),
        default="gpt-3.5-turbo", scope=Scope.settings,
        help=_("AI model to use.")
    )

    temperature = Float(
        display_name=_('Temperature'),
        default=0.7,
        values={'min': 0.1, 'max': 2, 'step': 0.1},
        scope=Scope.settings,
        help=_('Controls randomness of output.')
    )

    description = String(
        display_name=_('Description'),
        default='Generate quiz questions using AI from a topic.',
        scope=Scope.settings,
        help=_('Optional description of this component.')
    )

    editable_fields = [
        'display_name',
        'context',
        'topic',
        'model_name',
        'api_key',
        'temperature',
        'description'
    ]

    def get_openai_client(self):
        try:
            return OpenAI(api_key=self.api_key)
        except Exception:
            return {'error': _('Failed to initialize OpenAI client')}

    def resource_string(self, path):
        try:
            data = importlib_resources.files(__name__).joinpath(path).read_bytes()
        except TypeError:
            data = importlib_resources.files(__package__).joinpath(path).read_bytes()
        return data.decode("utf8")

    def get_context(self):
        return {
            'title': self.display_name,
            'topic': self.topic,
            'generated_quiz': self.generated_quiz,
        }

    def render_template(self, template_path, context):
        template_str = self.resource_string(template_path)
        template = Template(template_str)
        return template.render(Context(self.get_context()))

    def student_view(self, context=None):
        html = self.render_template("static/html/ai_quiz_generator.html", context)
        frag = Fragment(html)
        frag.add_css(self.resource_string("static/css/ai_quiz_generator.css"))
        frag.add_javascript(self.resource_string("static/js/src/ai_quiz_generator.js"))
        frag.initialize_js('AIQuizGeneratorXBlock', json_args=self.get_context())
        return frag

    def get_chat_completion(self, prompt='', model='gpt-3.5-turbo', temperature=0.7, max_tokens=300):
        client = self.get_openai_client()
        if client is None:
            return {'error': _('Unable to initialize OpenAI client.')}

        messages = [{"role": "user", "content": prompt}]
        try:
            response = client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
        except Exception as err:
            log.error(err)
            return {'error': _('Unable to get quiz from AI. Check logs or API key.')}

        return {'response': response.choices[0].message.content}

    @XBlock.json_handler
    def generate_quiz(self, data, suffix=''):
        if not data.get('topic'):
            return {'error': _('Topic is required to generate a quiz.')}

        prompt = self.context.replace('{{topic}}', f'"{data["topic"]}"')
        result = self.get_chat_completion(prompt, self.model_name, self.temperature)

        if 'error' in result:
            return {'error': result['error']}

        self.generated_quiz = result['response']
        return {
            'success': True,
            'generated_quiz': self.generated_quiz
        }

    @staticmethod
    def workbench_scenarios():
        return [
            ("AIQuizGeneratorXBlock", """<ai_quiz_generator/>"""),
            ("Multiple Blocks", """
                <vertical_demo>
                    <ai_quiz_generator/>
                    <ai_quiz_generator/>
                </vertical_demo>
            """),
        ]

    def validate_field_data(self, validation, data):
        super().validate_field_data(validation, data)
        context = data.context.strip() if data.context else ""

        if "{{topic}}" not in context:
            validation.add(ValidationMessage(
                ValidationMessage.ERROR,
                "The prompt template must include the {{topic}} placeholder."
            ))
