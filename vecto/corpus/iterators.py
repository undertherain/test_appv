import os
import fnmatch
import collections
import logging

from vecto.corpus.base import BaseIterator
from vecto.corpus.tokenization import DEFAULT_TOKENIZER, DEFAULT_SENT_TOKENIZER
from vecto.utils.data import detect_archive_format_and_open


logger = logging.getLogger(__name__)


class FileIterator(BaseIterator):
    """
    Iterator which yields only given filename.
    """

    def __init__(self, filename, verbose=0):
        super(FileIterator, self).__init__(base_path=filename,
                                           verbose=verbose)
        self.filename = filename

    def _generate_samples(self):
        yield self.filename


class DirIterator(BaseIterator):
    """
    Iterator which yield all files in the given folder and all its subfolders.
    """

    def __init__(self, dirname, verbose=0):
        super(DirIterator, self).__init__(base_path=dirname,
                                          verbose=verbose)
        self.dirname = dirname

    def _generate_samples(self):
        for root, _, files in os.walk(self.dirname, followlinks=True):
            for good_fname in fnmatch.filter(files, "*"):
                full_file_path = os.path.join(root, good_fname)
                logger.info("processing " + full_file_path)
                yield full_file_path


class FileLineIterator(BaseIterator):
    """
    Receives a sequence of filenames from `base_corpus` and reads each file line-by-line.
    """

    def __init__(self, base_corpus, verbose=0):
        super(FileLineIterator, self).__init__(base_corpus=base_corpus.metadata,
                                               verbose=verbose)
        self.base_corpus = base_corpus

    def _generate_samples(self):
        for filename in self.base_corpus:
            with detect_archive_format_and_open(filename) as file_in:
                for line in file_in:
                    line = line.strip()
                    if line:
                        yield line


class TokenizedSequenceIterator(BaseIterator):
    """
    Receives any corpus yielding text (e.g. `FileLineIterator`) and produces tokenized sequences.
    Good for splitting texts on sentences.
    """

    def __init__(self, base_corpus, tokenizer=DEFAULT_TOKENIZER, verbose=0):
        super(TokenizedSequenceIterator, self).__init__(base_corpus=base_corpus.metadata,
                                                        tokenizer=tokenizer.metadata,
                                                        verbose=verbose)
        self.base_corpus = base_corpus
        self.tokenizer = tokenizer

    def _generate_samples(self):
        for line in self.base_corpus:
            # TODO: sentence may span over multiple lines, we should take this into account somehow
            # I think that it's better to ignore this here and write docs like:
            # "You should be aware of that and prepare your data accordingly, e.g. one line - one real doc"
            for tokenized_sentence in self.tokenizer(line.strip()):
                yield tokenized_sentence


class TokenIterator(BaseIterator):
    """
    Receives any corpus yielding text (e.g. `FileLineIterator`) and produces a sequence of tokens.
    """

    def __init__(self, base_corpus, verbose=0):
        super(TokenIterator, self).__init__(base_corpus=base_corpus.metadata,
                                            verbose=verbose)
        self.base_corpus = base_corpus

    def _generate_samples(self):
        for tokenized_str in self.base_corpus:
            for token in tokenized_str:
                yield token


def iter_sliding_window(seq, left_ctx_size, right_ctx_size):
    for i, current in enumerate(seq):
        ctx = []
        ctx.extend(seq[i - left_ctx_size: i])
        ctx.extend(seq[i + 1: i + right_ctx_size + 1])
        yield i, current, ctx


class SlidingWindowIterator(BaseIterator):
    """
    Receives any corpus yielding sequences of tokens (e.g. TokenizedSequenceIterator)
    and produces training samples for prediction-based distributional semantic models (like Word2Vec etc).
    Example of one yielded value: {'current': 'long', 'context': ['family', 'dashwood', 'settled', 'sussex']}
    """

    def __init__(self, base_corpus, left_ctx_size=2, right_ctx_size=2, verbose=0):
        assert isinstance(next(iter(base_corpus)), collections.abc.Sequence)
        super(SlidingWindowIterator, self).__init__(base_corpus=base_corpus.metadata,
                                                    left_ctx_size=left_ctx_size,
                                                    right_ctx_size=right_ctx_size,
                                                    verbose=verbose)
        self.base_corpus = base_corpus
        self.left_ctx_size = left_ctx_size
        self.right_ctx_size = right_ctx_size
        self.__gen__  = self._generate_samples()

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.__gen__)

    def _generate_samples(self):
        for sample_elems in self.base_corpus:
            for _, current, ctx in iter_sliding_window(sample_elems,
                                                       self.left_ctx_size,
                                                       self.right_ctx_size):
                yield dict(current=current,
                           context=ctx)


# class SlidingWindowAndGlobal(BaseIterator):
#     def __init__(self, base_corpus, left_ctx_size=2, right_ctx_size=2, verbose=0):
#         assert isinstance(next(iter(base_corpus)), collections.abc.Sequence)
#         super(SlidingWindowAndGlobal, self).__init__(base_corpus=base_corpus.metadata,
#                                                      left_ctx_size=left_ctx_size,
#                                                      right_ctx_size=right_ctx_size,
#                                                      verbose=verbose)
#         self.base_corpus = base_corpus
#         self.left_ctx_size = left_ctx_size
#         self.right_ctx_size = right_ctx_size

#     def _generate_samples(self):
#         for sample_elems in self.base_corpus:
#             for _, current, ctx in iter_sliding_window(sample_elems,
#                                                        self.left_ctx_size,
#                                                        self.right_ctx_size):
#                 yield dict(current=current,
#                            context=ctx,
#                            global_context=list(sample_elems))


# class IteratorChain(BaseIterator):
#    """
#    Like `itertools.chain`, but with proper metadata handling
#    """
#    def __init__(self, base_iterators, verbose=0):
#        super(IteratorChain, self).__init__(base_iterators=[i.metadata for i in base_iterators],
#                                            verbose=verbose)
#        self.base_iterators = base_iterators

#    def _generate_samples(self):
#        for base_iter in self.base_iterators:
#            for sample in base_iter:
#                yield sample


# class TruncatedCorpus(BaseIterator):
#    """
#    Reads first `limit` samples from `base_corpus` and yields them sample-by-sample.
#    Good for debugging.
#    """
#    def __init__(self, base_corpus, limit=1000, verbose=0):
#        super(TruncatedCorpus, self).__init__(base_corpus=base_corpus.meta,
#                                              verbose=verbose)
#        self.samples = []
#        for i, s in enumerate(base_corpus):
#            if i >= limit:
#                break
#            self.samples.append(s)
#        self.metadata['samples_count'] = len(self.samples)

#    def _generate_samples(self):
#        for s in self.samples:
#            yield s
