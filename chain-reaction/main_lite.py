import time

# 7.43PM
class Block:
    def __init__(self, name: str = None, description: str = None, retries: int = 3, retry_delay: int = 0, logging: bool = False):
        self.name = name
        self.retries = retries
        self.retry_delay = retry_delay
        self.logging = logging
        self.next_blocks = {}

    def prepare(self, context):
        pass
    
    def execute(self, context, prepare_response):
        pass
    
    def post_process(self, context, prepare_response, execute_response):
        return "default"

    def __run(self, context, prepare_response):
        execute_response = self.execute(context, prepare_response)
        return execute_response
    
    def run(self, context):
        prepare_response = self.prepare(context)

        execute_response = None

        attempts = 0

        while attempts < self.retries:
            try:
                attempts += 1
                execute_response = self.__run(context, prepare_response)
            except Exception as e:
                if attempts == self.retries:
                    execute_response = self.execute_fallback(context, prepare_response, e)
                    break
                time.sleep(self.retry_delay)
                continue
        
        post_process_response = self.post_process(context, prepare_response, execute_response)

        return post_process_response

    
    def execute_fallback(self, context, prepare_response, error):
        raise error
    
    def get_next_block(self, action: str):
        return self.next_blocks.get(action, None)
    
    def __sub__(self, action: str):
        return Helper(self, action)
    
    def __rshift__(self, other):
        self.next_blocks["default"] = other
        return self
    
class Helper:
    def __init__(self, src: Block, action: str):
        self.src = src
        self.action = action
    
    def __rshift__(self, other):
        self.src.next_blocks[self.action] = other
        return self
    
class Chain(Block):
    def __init__(self, name: str = None, description: str = None, starting_block: Block = None):
        super().__init__(name=name, description=description, retries=1, retry_delay=0)
        self.starting_block = starting_block
    
    def run(self, context):
        current_block = self.starting_block

        while current_block:
            post_process_response = current_block.run(context)
            current_block = current_block.get_next_block(post_process_response)

        return context
# end 7.56pm