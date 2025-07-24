from main import Chain
from apps.translator import Translator

# test code
if __name__ == "__main__":  # Fixed: __ not **

    # Simple block
    telugu = Translator(language="Telugu")
    context = {
        "text": "Hello, how are you?"
    }
    telugu.run(context=context)
    print(context)

    # Simple chain telugu -> hindi
    hindi = Translator(language="Hindi")
    telugu >> "default" >> hindi
    context = {
        "text": "I like music"
    }
    chain = Chain(starting_block=telugu)
    chain.run(context=context)
    print(context)