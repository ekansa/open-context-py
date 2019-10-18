# About Tests

The tests directory should be subdivided into 3 directories with different kinds of tests. This will be:

1. `/unit`: These will test functions and not require use of the database.
2. `/integration`: These are tests need a (temporary) database, but can work with fake data.
3. `/regression`: These tests will either require or will be easiest to conduct with real data in the Open Context database.
