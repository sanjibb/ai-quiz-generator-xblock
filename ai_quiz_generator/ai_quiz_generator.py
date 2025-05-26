import os
import tarfile
import tempfile
import uuid
import json
import logging

from xblock.fields import Float, String, Scope
from xblock.core import XBlock
from xblock.completable import CompletableXBlockMixin
from xblock.validation import ValidationMessage
from web_fragments.fragment import Fragment
from django.template import Context, Template
from django.conf import settings
#from django.http import HttpResponse as Response
from webob import Response
import openai
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
    topic = String(display_name=_('Prompt / Topic'), default='', scope=Scope.settings, multiline_editor=True)
    context = String(display_name=_('Prompt Template'), default="{{topic}}", scope=Scope.settings, multiline_editor=True)
    model_name = String(display_name=_("AI Model Name"), default="gpt-4o-mini", scope=Scope.settings)
    temperature = Float(display_name=_('Temperature'), default=0.7, values={'min': 0.1, 'max': 2, 'step': 0.1}, scope=Scope.settings)
    description = String(display_name=_('Description'), default='Generate quiz questions using AI from a topic.', scope=Scope.settings)
    generated_quiz = String(display_name=_('Generated Quiz'), default='', scope=Scope.user_state)

    editable_fields = ['display_name', 'context', 'topic', 'model_name', 'api_key', 'temperature', 'description']

    def get_openai_client(self):
        API_KEY=''
        try:
            return OpenAI(api_key=API_KEY)
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

    def get_chat_completion(self, prompt='', model='gpt-4o-mini', temperature=0.7, max_tokens=10000):
        
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
            log.error("Error during OpenAI completion: %s", err)
            return {'error': _('Unable to get quiz from AI. Check logs or API key.')}
        return {'response': response.choices[0].message.content}

    @XBlock.json_handler
    def generate_quiz(self, data, suffix=''):
        if not data.get('topic'):
            return {'error': _('Topic is required to generate a quiz.')}
        prompt = (
        "You are an quiz generator specialist."
        f"{self.context.replace('{{topic}}', data['topic'])}\n\n"
        f"Generate 5 quiz questions in the format below and output the questions in this JSON format."
        "{Question :question , choice_1: choice1, Choice_2: choice2 ...."
        "correct_answer: correct_answer explanation: explanation. "
        "Only pass the JSON record. do not pass anything else."
        "Also strip '''json  ''' "
        "enclose the whole thing with [ ]"              
        )
        self.context.replace('{{topic}}', data['topic'])
        result = self.get_chat_completion(prompt, self.model_name, self.temperature)
        if 'error' in result:
            return {'error': result['error']}
        self.generated_quiz = result['response']
        return {'success': True, 'generated_quiz': self.generated_quiz}

    def generate_course_files(self):
        print('quizes',self.generated_quiz)
        try:
            questions = json.loads(self.generated_quiz)
            print(questions)
            print('json load was successfull')
            
        except Exception as e:
            log.error("❌ JSON parsing failed:", exc_info=True)
            raise ValueError(f"Invalid JSON in generated_quiz: {e}")


        print(questions)
        print('json load was successfull')
            
        topic = self.topic or "Generated Quiz"
        course_dir = f"gpt_course_{uuid.uuid4().hex[:8]}"
        tar_path = f"{course_dir}.tar.gz"

        org = "GPT"
        course_code = "GEN101"
        course_url = "gpt_course"
        course_display_name = f"GPT Course: {topic}"
        chapter_id = "chapter1"
        sequential_id = "seq1"
        vertical_id = "vert1"
        chapter_display_name = "General Knowledge"
        sequential_display_name = topic
        vertical_display_name = f"{topic} Quiz"
        problem_ids = [f"q{i+1}" for i in range(len(questions))]

        for folder in ["course", "chapter", "sequential", "vertical", "problem", "about"]:
            os.makedirs(os.path.join(course_dir, folder), exist_ok=True)

        with open(os.path.join(course_dir, "course.xml"), "w") as f:
            f.write(f'<course url_name="{course_url}" org="{org}" course="{course_code}"/>')

        with open(os.path.join(course_dir, "course", f"{course_url}.xml"), "w") as f:
            f.write(f'''<course url_name="{course_url}" org="{org}" course="{course_code}" display_name="{course_display_name}">
            <chapter url_name="{chapter_id}"/>
            </course>
            ''')

        with open(os.path.join(course_dir, "about", "overview.html"), "w") as f:
            f.write(f"<h1>{course_display_name}</h1><p>This course contains a quiz on {topic}.</p>")

        with open(os.path.join(course_dir, "chapter", f"{chapter_id}.xml"), "w") as f:
            f.write(f'''<chapter display_name="{chapter_display_name}" url_name="{chapter_id}">
    <sequential url_name="{sequential_id}"/>
    </chapter>
    ''')

        with open(os.path.join(course_dir, "sequential", f"{sequential_id}.xml"), "w") as f:
            f.write(f'''<sequential display_name="{sequential_display_name}" url_name="{sequential_id}">
    <vertical url_name="{vertical_id}"/>
    </sequential>
    ''')
      
        with open(os.path.join(course_dir, "vertical", f"{vertical_id}.xml"), "w") as f:
            f.write(f'<vertical display_name="{vertical_display_name}" url_name="{vertical_id}">\n')
            for pid in problem_ids:
                f.write(f'  <problem url_name="{pid}"/>\n')
            f.write('</vertical>')
        
        # print('before writing quiz xml')
        # questions = """{
        # "Question": "What is the largest mammal in the world?",
        # "choice_1": "Elephant",
        # "choice_2": "Blue Whale",
        # "choice_3": "Giraffe",
        # "choice_4": "Great White Shark",
        # "correct_answer": "Blue Whale",
        # "explanation": "The Blue Whale is the largest mammal—and indeed, the largest animal—on Earth, reaching lengths of up to 100 feet."
        #      } """
        for pid, q in zip(problem_ids, questions):
            correct_answer_text = q["correct_answer"]
            choices = {
                "A": q["choice_1"],
                "B": q["choice_2"],
                "C": q["choice_3"],
                "D": q["choice_4"]
            }

            with open(os.path.join(course_dir, "problem", f"{pid}.xml"), "w") as f:
                xml = f'''<problem display_name="{q["Question"]}" url_name="{pid}">
    <multiplechoiceresponse>
        <label>{q["Question"]}</label>
        <choicegroup type="MultipleChoice">
    '''
                for letter, text in choices.items():
                    correct = "true" if text.strip() == correct_answer_text.strip() else "false"
                    xml += f'      <choice correct="{correct}">{text}</choice>\n'

                xml += f'''    </choicegroup>
        <solution>
        <div class="detailed-solution">
            <p>Explanation:</p>
            <p>{q["explanation"]}</p>
        </div>
        </solution>
    </multiplechoiceresponse>
    </problem>'''
                print('quiz_question', xml)
                f.write(xml)
                
        return course_dir

    @XBlock.handler
    def download_course_tar(self, request, suffix=''):
        if request.method != 'GET':
            return Response("Only GET requests are allowed for download.", status=405)

        try:    
            print('inside download')
            course_dir = self.generate_course_files()
            tar_path = f"{course_dir}.tar.gz"
            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(course_dir, arcname="course")

            with open(tar_path, 'rb') as f:
                data = f.read()

            response = Response(body=data, content_type="application/gzip")
            response.headers.add('Content-Disposition', f'attachment; filename=\"{os.path.basename(tar_path)}\"')
            return response
        except Exception as e:
            return Response(body=f"Error generating tarball: {str(e)}", status=500)

    @staticmethod
    def workbench_scenarios():
        return [("AIQuizGeneratorXBlock", """<ai_quiz_generator/>""")]

    def validate_field_data(self, validation, data):
        super().validate_field_data(validation, data)
        context = data.context.strip() if data.context else ""
        if not context:
            validation.add(ValidationMessage(ValidationMessage.ERROR, "The prompt template (context) must not be empty."))
