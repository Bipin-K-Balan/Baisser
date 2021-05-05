
import numpy as np
import tensorflow as tf
from pathlib import Path
from transformers import BertTokenizer, TFBertModel
from tensorflow.keras.layers import Dense, Dropout
import warnings
warnings.filterwarnings('ignore')
import logging
logging.getLogger('tensorflow').disabled = True

model_name = 'bert-base-cased'
tokenizer = BertTokenizer.from_pretrained(model_name)
intent_names = Path('vocab.intent').read_text('utf-8').split()
slot_names = ["[PAD]"]
slot_names += Path('vocab.slot').read_text('utf-8').strip().splitlines()


class JointIntentAndSlotFillingModel(tf.keras.Model):

    def __init__(self, intent_num_labels=None, slot_num_labels=None,
                 model_name="bert-base-cased", dropout_prob=0.1):
        super().__init__(name="joint_intent_slot")
        self.bert = TFBertModel.from_pretrained(model_name)
        self.dropout = Dropout(dropout_prob)
        self.intent_classifier = Dense(intent_num_labels,
                                       name="intent_classifier")
        self.slot_classifier = Dense(slot_num_labels,
                                     name="slot_classifier")

    def call(self, inputs, **kwargs):
        sequence_output, pooled_output = self.bert(inputs, **kwargs)

        # The first output of the main BERT layer has shape:
        # (batch_size, max_length, output_dim)
        sequence_output = self.dropout(sequence_output,
                                       training=kwargs.get("training", False))
        slot_logits = self.slot_classifier(sequence_output)

        # The second output of the main BERT layer has shape:
        # (batch_size, output_dim)
        # and gives a "pooled" representation for the full sequence from the
        # hidden state that corresponds to the "[CLS]" token.
        pooled_output = self.dropout(pooled_output,
                                     training=kwargs.get("training", False))
        intent_logits = self.intent_classifier(pooled_output)

        return slot_logits, intent_logits


class Baisser_bert():
    def __init__(self):
        self.new_model = JointIntentAndSlotFillingModel(
            intent_num_labels=13, slot_num_labels=42)
        self.new_model.load_weights("model/")

    def predictions(self,text):

        inputs = tf.constant(tokenizer.encode(text))[
            None, :]  # batch_size = 1
        outputs = self.new_model(inputs)
        slot_logits, intent_logits = outputs
        slot_ids = slot_logits.numpy().argmax(axis=-1)[0, 1:-1]
        intent_id = intent_logits.numpy().argmax(axis=-1)[0]

        #info = {"intent": intent_names[intent_id]}
        collected_slots = {}
        active_slot_words = []
        active_slot_name = None

        slots = []
        for word in text.split():
            # tokenize each word by word, some tokens of word contain list of subwords
            tokens = tokenizer.tokenize(word)
            current_word_slot_ids = slot_ids[:len(tokens)]
            slot_ids = slot_ids[len(tokens):]
            current_word_slot_name = slot_names[current_word_slot_ids[0]]
            slots.append(current_word_slot_name)
            # print(current_word_slot_name)
            # print(tokens)
        texts = text.split()
        st = set()
        if intent_names[intent_id] in ["response_yes","response_no"]:
            out = {}
            out["intent"] = intent_names[intent_id]
            return out
        else:

            out = {"slots":{}}
            out["intent"] = intent_names[intent_id]
            for slot, tex in zip(slots, texts):
                if slot == 'O':
                    pass
                elif slot[0] == 'I':
                    slot = slot[2:]
                    if slot in st:
                        out["slots"][slot][-1] = ' '.join([out["slots"][slot][-1], tex])
                    else:
                        st.add(slot)
                        out["slots"][slot] =[tex]
                elif slot[0] == 'B':
                    slot = slot[2:]
                    if slot not in st:
                        st.add(slot)
                        out["slots"][slot] = [tex]
                    else:
                        out["slots"][slot].append(tex)
            return out

