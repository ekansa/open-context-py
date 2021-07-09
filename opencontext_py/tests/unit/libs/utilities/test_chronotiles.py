import pytest

import random
import logging
from opencontext_py.libs.utilities import chronotiles

logger = logging.getLogger("tests-unit-logger")



TEST_ARGS = [
    (
        '5G',
        5 * pow(10, 9),
        [1,2,10,25,122,637,5000, 56.32 * pow(10, 6), 223.2 * pow(10, 6),]
    ),
    (
        '2.5G',
        2.5 * pow(10, 9),
        [1,2,10,25,432, 1252, 8.47 * pow(10, 6), 101.6 * pow(10, 6),]
    ),
    (
        '500M',
        500 * pow(10, 6),
        [1, 2, 10, 25, 897, 10256, 3.88 * pow(10, 6), 87.6 * pow(10, 6),]
    ),
    (
        '10M',
        10 * pow(10, 6),
        [1, 2, 10, 25, 751, 6752, 2.56 * pow(10, 3), 156.6 * pow(10, 3),]
    ),
    (
        '10k',
        10 * pow(10, 3),
        [1, 2, 10, 25, 121, 972, 2523, 6500,]
    ),
]

NUMBER_RANDOM_TEST_SPANS = 100


def test_encode_decode_paths():
    """Tests encoding and decoding of chronotile paths."""
    for prefix, path_max_bp, test_spans in TEST_ARGS:
        # Add NUMBER_RANDOM_TEST_SPANS more random test spans, 
        # with ranges up to 95 % the total time range allowed for the path duration
        test_spans += [
            random.randrange(1, (path_max_bp * 0.95), 1) 
            for i in range(NUMBER_RANDOM_TEST_SPANS)
        ]
        for test_span in test_spans:
            latest_bp = round(random.uniform(0, path_max_bp), 0)
            earliest_bp = round((latest_bp + test_span), 0)
            logger.info(
                f'Checking dates: {earliest_bp} to {latest_bp}'
            )
            if latest_bp > path_max_bp or earliest_bp > path_max_bp:
                # We expect an error to be raised in this case!
                logger.info(
                    f'Out of bound date should raise error (max bpp: {path_max_bp})'
                )
                with pytest.raises(Exception):
                     path = chronotiles.encode_path(
                        earliest_bp=earliest_bp,
                        latest_bp=latest_bp,
                        new_path=(f'{prefix}{chronotiles.PREFIX_DELIM}')
                    )
                continue

            path = chronotiles.encode_path(
                earliest_bp=earliest_bp,
                latest_bp=latest_bp,
                new_path=(f'{prefix}{chronotiles.PREFIX_DELIM}')
            )
            decode_dict = chronotiles.decode_path_dates(path)
            logger.info(
                f'Checking round-trip: {path}, length: '
                f'{chronotiles.raw_path_depth(path)}'
            )
            logger.info(
                f'Parsed dict: {decode_dict}'
            )
            # Assert that the round-trip of encoding to decoding worked!
            assert latest_bp == decode_dict['latest_bp']
            assert earliest_bp == decode_dict['earliest_bp']