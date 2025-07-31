# The idea is to define a base framework using which I should be able to create different llm based apps (rags, workflows etc)

# class block
# - prepare: gets required information from the shared storage. Example: reading files. querying DB. This emits prepare_response
# - execute: core compute. takes the output from prepare as context. doesn't read/write to storage directly. ex: llm calls. This emits execute_response. This is where retries are handled and any exceptions (if any) are raised.
# - post_process: takes the output from execute and does some post processing. ex: formatting the output. This takes in response from prepare and execute's and makes any updates as required to the shared context. And decides on next steps.
# - execute_fallback: if execute fails even after retries, then this is called to see if there is a fallback plan. if not, the error is percolated up.

import time
from datetime import datetime

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
        # Initialize timing context if not exists
        if 'timing' not in context:
            context['timing'] = {}
        if 'logs' not in context:
            context['logs'] = []
            
        block_start_time = time.time()
        
        if self.logging:
            print(f"Running block {self.name}")
            
        # Add log entry for block start
        context['logs'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'block': self.name,
            'event': 'block_started',
            'message': f'Started executing block: {self.name}'
        })
        
        # Time prepare phase
        prepare_start = time.time()
        prepare_response = self.prepare(context)
        prepare_duration = time.time() - prepare_start
        
        # if self.logging:
        #     print(f"Prepare response: {prepare_response}")
            
        context['logs'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'block': self.name,
            'event': 'prepare_completed',
            'duration_ms': round(prepare_duration * 1000, 2),
            'message': f'Prepare phase completed in {round(prepare_duration * 1000, 2)}ms'
        })


        self.current_attempt = 0
        execute_response = None
        execute_error = None
        execute_start = time.time()

        # define a lambda that will retry the execute call
        retry_execute = lambda: self.execute(context, prepare_response)

        while self.current_attempt < self.retries:
            try:
                attempt_start = time.time()
                execute_response = retry_execute()
                attempt_duration = time.time() - attempt_start
                
                if self.logging:
                    print(f"Execute response attempt {self.current_attempt}: {execute_response}")
                    
                context['logs'].append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'block': self.name,
                    'event': 'execute_attempt_success',
                    'attempt': self.current_attempt + 1,
                    'duration_ms': round(attempt_duration * 1000, 2),
                    'message': f'Execute attempt {self.current_attempt + 1} succeeded in {round(attempt_duration * 1000, 2)}ms'
                })
                
                execute_error = None
                break
            except Exception as e:
                execute_error = e
                self.current_attempt += 1
                
                context['logs'].append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'block': self.name,
                    'event': 'execute_attempt_failed',
                    'attempt': self.current_attempt,
                    'error': str(e),
                    'message': f'Execute attempt {self.current_attempt} failed: {str(e)}'
                })
                
                time.sleep(self.retry_delay)

        if execute_error:
            fallback_start = time.time()
            execute_response = self.execute_fallback(context, prepare_response, execute_error)
            fallback_duration = time.time() - fallback_start
            
            if self.logging:
                print(f"Execute fallback response: {execute_response}")
                
            context['logs'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'block': self.name,
                'event': 'execute_fallback',
                'duration_ms': round(fallback_duration * 1000, 2),
                'message': f'Execute fallback completed in {round(fallback_duration * 1000, 2)}ms'
            })

        execute_duration = time.time() - execute_start
        
        # Time post-process phase
        post_process_start = time.time()
        post_process_response = self.post_process(context, prepare_response, execute_response)
        post_process_duration = time.time() - post_process_start
        
        if self.logging:
            print(f"Post process response: {post_process_response}")
            
        context['logs'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'block': self.name,
            'event': 'post_process_completed',
            'duration_ms': round(post_process_duration * 1000, 2),
            'message': f'Post-process phase completed in {round(post_process_duration * 1000, 2)}ms'
        })

        # Calculate total block duration
        block_duration = time.time() - block_start_time
        
        # Store timing info in context
        context['timing'][self.name] = {
            'total_ms': round(block_duration * 1000, 2),
            'prepare_ms': round(prepare_duration * 1000, 2),
            'execute_ms': round(execute_duration * 1000, 2),
            'post_process_ms': round(post_process_duration * 1000, 2)
        }
        
        context['logs'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'block': self.name,
            'event': 'block_completed',
            'duration_ms': round(block_duration * 1000, 2),
            'message': f'Block {self.name} completed in {round(block_duration * 1000, 2)}ms'
        })

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
        chain_start_time = time.time()
        
        # Initialize chain-level timing
        if 'chain_timing' not in context:
            context['chain_timing'] = {
                'start_time': datetime.utcnow().isoformat(),
                'blocks_executed': []
            }
        
        current_block = self.starting_block
        action = None
        block_count = 0
        
        while True:
            block_name = current_block.name or f"Block_{block_count}"
            context['chain_timing']['blocks_executed'].append(block_name)
            
            action = current_block.run(context)
            if action is None:
                action = "default"
            # Ask current_block if there's a next block
            next_block = current_block.get_next_block(action)
            if next_block is None:
                # complete the chain
                break
            current_block = next_block
            block_count += 1
            
        # Calculate total chain duration
        chain_duration = time.time() - chain_start_time
        context['chain_timing']['total_duration_ms'] = round(chain_duration * 1000, 2)
        context['chain_timing']['end_time'] = datetime.utcnow().isoformat()
        
        # Add final log entry
        context['logs'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'block': 'Chain',
            'event': 'chain_completed',
            'duration_ms': round(chain_duration * 1000, 2),
            'blocks_executed': block_count + 1,
            'message': f'Chain completed: executed {block_count + 1} blocks in {round(chain_duration * 1000, 2)}ms'
        })
        
        return action


