from setuptools import setup, find_packages

setup(
    name= "excepthook",
    version= "1.0.0",
    description= "Enhanced exception handler with intelligent LLM that can fix errors and enhance output",
    long_description= open("README.md").read(),
    long_description_content_type= "text/markdown",
    author= "Richmond Koomson",
    author_email= "rkoomson777@gmail.com",
    packages= find_packages(include= []),
    url= "https://github.com/khonello/ExceptHook",
    py_modules= ["install"],
    include_package_data= True,
    install_requires= ["rich", "langchain", "langchain_groq", "dotenv"],
    python_requires= ">=3.10",
    entry_points = {
        "console_scripts": [
            "install_hook=install:write_sitecustomize"
        ]
    }
)