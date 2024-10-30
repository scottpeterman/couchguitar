from setuptools import setup, find_packages

setup(
    name="couchguitar",
    version="0.1.0",
    author="Scott Peterman",
    author_email="your_email@example.com",
    description="A small PyQt6 app for musicians to display songs teleprompter style,and make short recordings to play along with",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/scottpeterman/couchguitar",
    packages=find_packages(include=["couchguitar", "couchguitar.*"]),
    install_requires=open("requirements.txt").readlines(),
    package_data={
        "couchguitar": ["resource/dark/demo.qss", "resource/light/demo.qss", "resource/guitar.png", "songs/*.txt", "intro.wav"]
    },
    entry_points={
        "console_scripts": [
            "couchguitar = couchguitar.main:main"
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    license="GPLv3",

)
