from setuptools import setup

def get_requirements():
    with open('requirements.txt') as f:
        requirements = f.read().splitlines()
    return requirements

setup(
    name='Red-Lavalink',
    version='0.0.4',
    packages=['lavalink',],
    url='https://github.com/Cog-Creators/Red-Lavalink',
    license='GPLv3',
    author='tekulvw',
    description='Lavalink client library for Red-DiscordBot',
    include_package_data=True,
    python_requires='>3.5.1',
    install_requires=get_requirements(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: AsyncIO',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.5',
        'Topic :: Multimedia :: Sound/Audio :: Players',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    extras_require={
        'tests': ['pytest>3.0.6', 'pytest-asyncio', 'async_generator'],
        'docs': ['sphinx', 'sphinxcontrib-asyncio', 'sphinx_rtd_theme']
    }
)
