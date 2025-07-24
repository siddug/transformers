from main import Chain
from apps.translator import Translator
from apps.grounded_gpt import Search, Draft, Main

# test code
if __name__ == "__main__":  # Fixed: __ not **

    # Simple block
    # telugu = Translator(language="Telugu")
    # context = {
    #     "text": "Hello, how are you?"
    # }
    # telugu.run(context=context)
    # print(context)

    # Simple chain telugu -> hindi
    # hindi = Translator(language="Hindi")
    # telugu >> "default" >> hindi
    # context = {
    #     "text": "I like music"
    # }
    # chain = Chain(starting_block=telugu)
    # chain.run(context=context)
    # print(context)

    # Simple chain with search
    search = Search(retries=3)
    draft = Draft(retries=3)
    main = Main()
    search >> main
    main - "draft" >> draft
    main - "search" >> search
    context = {
        "query": "What is the capital of India?"
    }
    chain = Chain(starting_block=main)
    chain.run(context=context)
    print(context)