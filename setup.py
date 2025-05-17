"""Setup for ai_quiz_generator XBlock."""

import os
from pathlib import Path
from setuptools import find_packages, setup

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()


def package_data(pkg, roots):
    """Generic function to find package_data.

    All of the files under each of the `roots` will be declared as package
    data for package `pkg`.
    """
    data = []
    for root in roots:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}


setup(
    name='ai-quiz-generator-xblock',
    version='1.0.0',
    description="AI Quiz Generator XBlock creates multiple choice questions using OpenAI",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/sanjibb/ai-quiz-generator-xblock',
    license='AGPL v3',
    author='sanjib basak',
    packages=find_packages(
        include=['ai_quiz_generator', 'ai_quiz_generator.*'],
        exclude=["*tests"],
    ),
    install_requires=[
        'XBlock',
        'xblock-utils',
        'openai>=1.0.0,<2.0.0'
    ],
    entry_points={
        'xblock.v1': [
            'ai_quiz_generator = ai_quiz_generator:AIQuizGeneratorXBlock',
        ]
    },
    package_data=package_data("ai_quiz_generator", ["static", "public"]),
)
