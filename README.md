# language-trainer

## Motivation

Most AI training pipelines focus on the opposite direction:  
humans provide feedback, and the AI model improves.  

This project explores a reversed perspective:  
**an AI system trains the human.**

The core idea is simple:  
- The AI generates short exercises with missing words or phrases.  
- The human fills the gaps.  
- The AI adapts the difficulty based on the human’s responses.  

The goal is to create a supportive, low-stress environment for language practice.  
Instead of points or scores, the focus is on **clarity, repetition, and gradual progress**.  

At the beginning, the system offers very short, familiar sentences with a single missing word.  
Over time, the exercises may expand towards more complex sentences and eventually short texts,  
mirroring how large language models are trained on longer sequences.  

This way, the project becomes a kind of **reverse language model fine-tuning**:  
not the model learns from humans, but the human learns with the guidance of the model.
