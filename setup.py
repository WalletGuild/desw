from setuptools import setup

classifiers = [
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 2",
    "Topic :: Software Development :: Libraries",
]

setup(
    name='DeSW',
    version='0.0.1.1',
    packages=['desw', 'desw.plugins'],
    url='https://bitbucket.org/deginner/desw',
    license='MIT',
    classifiers=classifiers,
    author='deginner',
    author_email='support@deginner.com',
    description='An HTTP server application using Swagger 2.0, bitjws, and SQLAlchemy.',
    setup_requires=['pytest-runner'],
    package_data={'desw': ['static/swagger.json']},
    install_requires=[
        'sqlalchemy>=1.0.9',
        'secp256k1==0.11',
        "bitjws==0.6.3.1",
        "flask>=0.10.0",
        "flask-login",
        "flask-cors",
        "flask-bitjws>=0.1.1.4",
        "alchemyjsonschema"
    ],
    tests_require=['pytest', 'pytest-cov'],
    extras_require={"build": ["flask-swagger"]}
)
