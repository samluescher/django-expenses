from distutils.core import setup

setup(
    name='django-expenses',
    version='0.9.0',
    author='Samuel Luescher',
    author_email='sam@luescher.org',
    packages=['expenses'],
    scripts=[],
    url='http://github.com/samluescher/django-expenses',
    license='LICENSE',
    description='',
    long_description=open('README.md').read(),
    install_requires=[
        "Django >= 1.3"
    ],
)