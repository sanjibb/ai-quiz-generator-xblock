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
    display_name = String(display_name=_('Display Name'), default="AI Quiz Generator", scope=Scope.settings)

    topic = String(display_name=_('Quiz Topic'), default='', scope=Scope.settings, multiline_editor=True)
    generated_quiz = String(display_name=_('Generated Quiz'), default='', scope=Scope.user_state)

    context = String(
        display_name=_('Prompt Template'),
        default="""Generate {{num_quizzes}} multiple-choice questions on the topic below:\nTopic: {{topic}}\n\nFormat:\nQuestion:\nA.\nB.\nC.\nD.\nCorrect Answer:""",
        scope=Scope.settings,
        multiline_editor=True
    )

    num_quizzes = Integer(display_name=_('Number of Quizzes'), default=1, scope=Scope.settings)

    api_key = String(display_name=_("API Key"), default=getattr(settings, 'OPENAI_SECRET_KEY', ''), scope=Scope.settings)
    model_name = String(display_name=_("AI Model Name"), default="gpt-4o", scope=Scope.settings)
    temperature = Float(display_name=_('Temperature'), default=0.7, values={'min': 0.1, 'max': 2, 'step': 0.1}, scope=Scope.settings)

    editable_fields = ['display_name', 'context', 'topic', 'model_name', 'api_key', 'temperature', 'num_quizzes']

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
            'num_quizzes': self.num_quizzes
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

    def get_chat_completion(self, prompt='', model='gpt-4o', temperature=0.7, max_tokens=500):
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
            return {'error': _('Unable to get quiz from AI.')}

        return {'response': response.choices[0].message.content}

    @XBlock.json_handler
    def generate_quiz(self, data, suffix=''):
        topic = data.get('topic', '').strip()
        num_quizzes = data.get('num_quizzes', self.num_quizzes)

        if not topic:
            return {'error': _('Topic is required.')}

        prompt = self.context.replace('{{topic}}', f'"{topic}"').replace('{{num_quizzes}}', str(num_quizzes))
        result = self.get_chat_completion(prompt, self.model_name, self.temperature)

        if 'error' in result:
            return {'error': result['error']}

        self.generated_quiz = result['response']
        return {'success': True, 'generated_quiz': self.generated_quiz}

    @XBlock.json_handler
    def confirm_quiz(self, data, suffix=''):
        quiz = data.get("quiz", "").strip()
        if not quiz:
            return {'error': _('No quiz content to confirm.')}

        try:
            from xmodule.modulestore.django import modulestore
            store = modulestore()
            usage_key = self.scope_ids.usage_id
            parent = store.get_parent(usage_key)

            store.create_item(
                user_id=None,
                parent_location=parent.location,
                block_type='problem',
                fields={
                    'display_name': 'AI Generated Quiz',
                    'data': quiz
                }
            )

            return {'success': True}
        except Exception as e:
            log.error(f"Failed to add quiz: {e}")
            return {'error': _('Failed to add quiz to unit.')}

    @staticmethod
    def workbench_scenarios():
        return [
            ("AIQuizGeneratorXBlock", """<ai_quiz_generator/>"""),
            ("Multiple Blocks", """<vertical_demo><ai_quiz_generator/><ai_quiz_generator/></vertical_demo>"""),
        ]

    def validate_field_data(self, validation, data):
        super().validate_field_data(validation, data)
        context = data.context.strip() if data.context else ""
        if "{{topic}}" not in context:
            validation.add(ValidationMessage(ValidationMessage.ERROR, "Prompt must include {{topic}}."))
        if "{{num_quizzes}}" not in context:
            validation.add(ValidationMessage(ValidationMessage.ERROR, "Prompt must include {{num_quizzes}}."))

