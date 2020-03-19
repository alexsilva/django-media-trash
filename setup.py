from setuptools import setup

setup(
    name='django-media-trash',
    version='2.0',
    packages=['media_trash',
              'media_trash.management',
              'media_trash.management.commands',
              'media_trash.templatetags'],
    url='https://github.com/alexsilva/django-media-trash',
    license='MIT',
    author='alex',
    author_email='alex@fabricadigital.com.br',
    description='Django app to move media files to a recycle bin and restore when needed.',
    include_package_data=True
)
