# ExceptHook

#### Description
This replaces the exception hook with one with a nice traceback and LLM integration for fixing errors

##### Usage
In any module that you are working in, when you run the module and an exception is triggered, the custom exception handler will be triggered. By default when the handler is triggered, the default traceback is printed but with a little enhancement using the `rich` library.

##### Options
If anywhere in your code there are any of these options trigger different behaviours.
- `#: fix`
- `#: enhance`
- `#: explain`

##### Fix
This will contact `Groq` LLM to fix the exception code.

##### Enhance
This will enhance the traceback in a well structured way.

##### Explain
This will provide an explanation on what triggered the exception and how to fix it as comment at the top.

#### Environment
Create a virtual environment and activate it

#### Method 1
- Clone the project and build the package locally then install using this command `pip install .`

#### Method 2
- Install from PyPI using this command `pip install excepthook`.

#### Setup 
- Create a `.env` file with your `GROQ_API_KEY`
- Run `install_hook` to write the `sitecustomize.py` in the `sitepackages` directory which will be providing the features.

```
Python

#: enhance
#: fix

def foo(*args, **kwargs):

    if not args:
        raise ValueError("No argument provided")

foo()
```
> Sample python code to illustrate

Note: Enusre you have created a virtual environment, activated it and installed the packge in it.
