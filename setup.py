from setuptools import setup

setup(
    name='cli-suggest',
    version='0.1.3',
    py_modules=['cli_suggest'],
    install_requires=[
        'anthropic',
        'ratelimit',
    ],
    entry_points={
        'console_scripts': [
            'cli-suggest=cli_suggest:main',
        ],
    },
)