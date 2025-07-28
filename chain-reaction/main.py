# The idea is to define a base framework using which I should be able to create different llm based apps (rags, workflows etc)

# class block
# - prepare: gets required information from the shared storage. Example: reading files. querying DB. This emits prepare_response
# - execute: core compute. takes the output from prepare as context. doesn't read/write to storage directly. ex: llm calls. This emits execute_response. This is where retries are handled and any exceptions (if any) are raised.
# - post_process: takes the output from execute and does some post processing. ex: formatting the output. This takes in response from prepare and execute's and makes any updates as required to the shared context. And decides on next steps.
# - execute_fallback: if execute fails even after retries, then this is called to see if there is a fallback plan. if not, the error is percolated up.

import time

class Block:
    def __init__(self, name: str = None, description: str = None, retries: int = 1, retry_delay: int = 0, logging: bool = False):
        self.name = name
        self.description = description
        self.retries = retries
        self.retry_delay = retry_delay
        self.logging = logging
        self.next_blocks = {}

    def prepare(self, context):
        pass

    def execute(self, context, prepare_response):
        pass
    
    def post_process(self, context, prepare_response, execute_response):
        pass
    
    def run(self, context):
        if self.logging:
            print(f"Running block {self.name}")
        prepare_response = self.prepare(context)
        if self.logging:
            print(f"Prepare response: {prepare_response}")


        self.current_attempt = 0
        execute_response = None
        execute_error = None

        # define a lambda that will retry the execute call
        retry_execute = lambda: self.execute(context, prepare_response)

        while self.current_attempt < self.retries:
            try:
                execute_response = retry_execute()
                if self.logging:
                    print(f"Execute response attempt {self.current_attempt}: {execute_response}")
                execute_error = None
                break
            except Exception as e:
                execute_error = e
                self.current_attempt += 1
                time.sleep(self.retry_delay)

        if execute_error:
            execute_response = self.execute_fallback(context, prepare_response, execute_error)
            if self.logging:
                print(f"Execute fallback response: {execute_response}")

        post_process_response = self.post_process(context, prepare_response, execute_response)
        if self.logging:
            print(f"Post process response: {post_process_response}")

        return post_process_response

    def execute_fallback(self, context, prepare_response, error):
        #  by default just raise the error
        raise error

    def get_next_block(self, next_block: str):
        return self.next_blocks.get(next_block, None)
    
    # This takes care of a - "name" part of a - "name" >> b
    def __sub__(self, action: str):
        return HelperDefinition(self, action)

    # This is for the case a >> b
    def __rshift__(self, other):
        self.next_blocks["default"] = other
        return self

# Handy helper so that we can easily define chaining b/n blocks like a - "name" >> b
class HelperDefinition:
    def __init__(self, src: Block, action: str):
        self.src = src
        self.action = action

    def __rshift__(self, other):
        self.src.next_blocks[self.action] = other
        return self.src


class Chain(Block):
    def __init__(self, name: str = None, description: str = None, starting_block: Block = None):
        super().__init__(name=name, description=description, retries=1, retry_delay=0)
        self.starting_block = starting_block

    def start(self, start: Block):
        self.starting_block = start
        return start
    
    def execute(self, context, prepare_response):
        current_block = self.starting_block
        action = None
        while True:
            action = current_block.run(context)
            if action is None:
                action = "default"
            # Ask current_block if there's a next block
            next_block = current_block.get_next_block(action)
            if next_block is None:
                # complete the chain
                break
            current_block = next_block
        return action


