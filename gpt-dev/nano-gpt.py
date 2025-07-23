import torch
import torch.nn as nn
import torch.nn.functional as F

# hyperparameters
torch.manual_seed(1337)
batch_size = 64
block_size = context_length = 256 # context length of 1-8 are fed into the NN
max_iters = 5000
eval_interval = 500
learning_rate = 3e-3
device = 'cuda' if torch.cuda.is_available() else 'cpu'
eval_iters = 200
n_embd = 384
n_head = 6
n_layer = 6
dropout = 0.2

# Data reading
with open('input.txt', 'r', encoding='utf-8') as f:
    text = f.read()
chars = sorted(list(set(text)))
vocab_size = len(chars)

# create a mapping from characters to integers
stoi = { ch:i for i,ch in enumerate(chars) }
itos = { i:ch for i,ch in enumerate(chars) }
encode = lambda s: [stoi[c] for c in s] # encoder: take a string, output a list of integers
decode = lambda l: ''.join([itos[i] for i in l]) # decoder: take a list of integers, output a string

# entire dataset is encoded into a tensor
data = torch.tensor(encode(text), dtype=torch.long)

# split the data into train, validation and test sets
train_data = data[:int(0.8*len(data))]
val_data = data[int(0.8*len(data)):int(0.9*len(data)    )]
test_data = data[int(0.9*len(data)):]

# data loading
def get_batch(split):
  data = train_data if split == 'train' else val_data if split == 'val' else test_data
  ix = torch.randint(len(data) - block_size, (batch_size,))
  x = torch.stack([data[i:i+block_size] for i in ix])
  y = torch.stack([data[i+1:i+block_size+1] for i in ix])
  x, y = x.to(device), y.to(device)
  return x, y



# evaluate the loss
@torch.no_grad()
def estimate_loss():
  out = {}
  model.eval()
  for split in ['train', 'val']:
    losses = torch.zeros(eval_iters)
    for k in range(eval_iters):
      X, Y = get_batch(split)
      logits, loss = model(X, Y)
      losses[k] = loss.item()
    out[split] = losses.mean()
  model.train()
  return out

class Block(nn.Module):
  def __init__(self, n_embd, n_head):
    super().__init__()
    head_size = n_embd // n_head
    self.ma = MultiHeadAttention(n_head, head_size)
    self.ffwd = FeedForward(n_embd)
    self.ln1 = nn.LayerNorm(n_embd)
    self.ln2 = nn.LayerNorm(n_embd)
  
  def forward(self, x):
    x = x + self.ma(self.ln1(x))
    x = x + self.ffwd(self.ln2(x))
    return x

class FeedForward(nn.Module):
  def __init__(self, n_embd):
    super().__init__()
    self.net = nn.Sequential(
      nn.Linear(n_embd, 4 * n_embd),
      nn.ReLU(),
      nn.Linear(4 * n_embd, n_embd),
      nn.Dropout(dropout)
    )

  def forward(self, x):
    x = self.net(x) # pass through the network
    return x

class MultiHeadAttention(nn.Module):
  def __init__(self, num_heads, head_size):
    super().__init__()
    self.heads = nn.ModuleList([Head(head_size) for _ in range(num_heads)])
    self.proj = nn.Linear(n_embd, n_embd)
    self.dropout = nn.Dropout(dropout)

  def forward(self, x):
    out = torch.cat([h(x) for h in self.heads], dim=-1)
    out = self.proj(out)
    out = self.dropout(out)
    return out
    

class Head(nn.Module):
  def __init__(self, head_size):
    super().__init__()
    self.key = nn.Linear(n_embd, head_size, bias=False)
    self.query = nn.Linear(n_embd, head_size, bias=False)
    self.value = nn.Linear(n_embd, head_size, bias=False)
    self.register_buffer('tril', torch.tril(torch.ones(block_size, block_size)))
    self.dropout = nn.Dropout(dropout)

  def forward(self, x):
    B, T, C = x.shape
    k = self.key(x) # (B, T, C)
    q = self.query(x) # (B, T, C)
    v = self.value(x) # (B, T, C)
    wei = q @ k.transpose(-2, -1) * C**-0.5
    wei = wei.masked_fill(self.tril[:T, :T] == 0, float('-inf'))
    wei = F.softmax(wei, dim=-1)
    wei = self.dropout(wei)
    v = self.value(x) # (B, T, C)
    out = wei @ v
    return out

# Simple bigram model
class BigramLanguageModel(nn.Module):
  def __init__(self):
    super().__init__()
    # each token directly reads off the logits for the next token from a look up table
    self.token_embedding_table = nn.Embedding(vocab_size, n_embd)
    self.position_embedding_table = nn.Embedding(block_size, n_embd)
    self.blocks = nn.Sequential(*[Block(n_embd, n_head) for _ in range(n_layer)])
    self.ln = nn.LayerNorm(n_embd)
    self.lm_head = nn.Linear(n_embd, vocab_size)

  def forward(self, idx, targets=None):
    B, T = idx.shape

    token_embeddings = self.token_embedding_table(idx) # (B, T, C)
    position_embeddings = self.position_embedding_table(torch.arange(T, device=device)) # (T, C)
    x = token_embeddings + position_embeddings # (B, T, C)
    x = self.blocks(x)
    x = self.ln(x)
    logits = self.lm_head(x) # (B, T, vocab_size)

    loss = None
    if targets is None:
      loss = None
    else:
      # B = Batch size
      # T = context size
      # C = embedding size
      B, T, C = logits.shape
      # Flattening all the embeddings of the inputs characters in the block. so it's 2D.
      # one dimension is all the entries batchxcontext flattened. other dimension are the embeddings for each one of them.
      logits = logits.view(B*T, C)
      # Flattening all the targets characters in the block
      targets = targets.view(B*T)
      # Loss calc = NLL. -log(1/65)
      loss = F.cross_entropy(logits, targets)
    return logits, loss

  def generate(self, idx, max_new_tokens):
    # idx is (B, T) array of indices in the current context
    for _ in range(max_new_tokens):
      # crop idx to the last block_size tokens
      idx_cond = idx[:, -block_size:]
      # get the predictions
      logits, loss = self(idx_cond)
      # focus only on the last time step
      logits = logits[:, -1, :] # becomes (B, C)
      # apply softmax to get probabilities
      probs = F.softmax(logits, dim=-1) # (B, C)
      # sample from the distribution
      idx_next = torch.multinomial(probs, num_samples=1) # (B, 1)
      # append sampled index to the running sequence
      idx = torch.cat((idx, idx_next), dim=1) # (B, T+1)
    return idx

model = BigramLanguageModel()
model.to(device)


def train_model():
    # create a PyTorch optimizer
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)

    for iter in range(max_iters):
        # every eval_interval, check the loss on the validation set
        if iter % eval_interval == 0:
            losses = estimate_loss()
            print(f"step {iter} train loss: {losses['train']:.4f} val loss: {losses['val']:.4f}")
        
        # sample a batch of data
        xb, yb = get_batch('train')

        # evaluate the loss
        logits, loss = model(xb, yb)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()

def predict():
    idx = torch.zeros((1, 1), dtype=torch.long, device=device)
    print(decode(model.generate(idx, max_new_tokens=300)[0].tolist()))

train_model()
predict()