import git2net
import pathpy as pp
import pytest
import pydriller
import numpy as np
import lizard
import os
from datetime import datetime

@pytest.yield_fixture(scope="module")
def repo_string():
    yield 'test_repos/test_repo_1'

@pytest.yield_fixture(scope="module")
def sqlite_db_file():
    yield 'tests/test_repo_1.db'


def test_get_commit_dag(repo_string):
    dag = git2net.get_commit_dag(repo_string)
    expected_edges = [('e4448e8', 'f343ed5'), ('f343ed5', '6b531fc'), ('6b531fc', 'b17c2c3'),
                      ('b17c2c3', '2b00f48'), ('2b00f48', '59da499'), ('2b00f48', 'b21583e'),
                      ('b21583e', '7d140b9'), ('59da499', '7d140b9'), ('7d140b9', '9e28e38'),
                      ('7d140b9', '16bbc87'), ('9e28e38', '080220d'), ('16bbc87', '080220d'),
                      ('16bbc87', 'eadd9d4'), ('080220d', '02b4a6f'), ('02b4a6f', '9798c44'),
                      ('eadd9d4', '9798c44'), ('9798c44', '2f4f139'), ('9798c44', '2ce5105'),
                      ('2ce5105', '9602507'), ('2f4f139', '9602507'), ('9602507', '2edf3d9'),
                      ('9602507', '2c3300a'), ('9602507', '00f3bbe'), ('2c3300a', '4b5f698'),
                      ('2edf3d9', '4b5f698'), ('00f3bbe', 'deff6c8'), ('2edf3d9', 'deff6c8'),
                      ('4b5f698', 'dcf060d'), ('deff6c8', 'dcf060d'), ('dcf060d', '5606e82'),
                      ('5606e82', '1adc153'), ('5606e82', 'e8be9c6'), ('e8be9c6', '97b5e43'),
                      ('1adc153', '97b5e43'), ('97b5e43', '1c038ed'), ('1c038ed', '94a9da2'),
                      ('94a9da2', '83214bc')]
    dag.topsort()
    assert list(dag.edges.keys()) == expected_edges
    assert dag.is_acyclic


def test_extract_edits_1(repo_string):
    commit_hash = 'b17c2c321ce8d299de3d063ca0a1b0b363477505'
    filename = 'first_lines.txt'

    git_repo = pydriller.GitRepository(repo_string)
    commit = git_repo.get_commit(commit_hash)
    for mod in commit.modifications:
        if mod.filename == filename:
            df = git2net.extraction._extract_edits(git_repo, commit, mod, use_blocks=False,
                                                  blame_C='CCC4')
    assert len(df) == 3
    print(df)
    assert df.at[0, 'original_commit_addition'] == 'e4448e87541d19d139b9d033b2578941a53d1f97'
    assert df.at[1, 'original_commit_addition'] == '6b531fcb57d5b9d98dd983cb65357d82ccca647b'
    assert df.at[2, 'original_commit_addition'] == 'e4448e87541d19d139b9d033b2578941a53d1f97'


def test_extract_edits_2(repo_string):
    commit_hash = 'b17c2c321ce8d299de3d063ca0a1b0b363477505'
    filename = 'first_lines.txt'

    git_repo = pydriller.GitRepository(repo_string)
    commit = git_repo.get_commit(commit_hash)
    df = None
    for mod in commit.modifications:
        if mod.filename == filename:
            df = git2net.extraction._extract_edits(git_repo, commit, mod, use_blocks=True,
                                                  blame_C='CCC4')
    assert len(df) == 1
    assert df.at[0, 'original_commit_addition'] == 'not available with use_blocks'


def test_identify_edits(repo_string):
    commit_hash = 'f343ed53ee64717f85135c4b8d3f6bd018be80ad'
    filename = 'text_file.txt'

    git_repo = pydriller.GitRepository(repo_string)
    commit = git_repo.get_commit(commit_hash)
    for x in commit.modifications:
        if x.filename == filename:
            mod = x

    parsed_lines = git_repo.parse_diff(mod.diff)

    deleted_lines = { x[0]:x[1] for x in parsed_lines['deleted'] }
    added_lines = { x[0]:x[1] for x in parsed_lines['added'] }

    _, edits = git2net.extraction._identify_edits(deleted_lines, added_lines, use_blocks=False)
    assert list(edits.type) == ['deletion', 'replacement', 'deletion', 'replacement', 'addition',
                                'addition', 'addition']


def test_process_commit(repo_string):
    commit_hash = 'f343ed53ee64717f85135c4b8d3f6bd018be80ad'
    args = {'repo_string': repo_string, 'commit_hash': commit_hash, 'use_blocks': False,
             'exclude_paths': [], 'blame_C': '-C'}
    res_dict = git2net.extraction._process_commit(args)
    assert list(res_dict.keys()) == ['commit', 'edits']


def test_get_unified_changes(repo_string):
    commit_hash = 'e8be9c6abe76c809a567866e411350e76eb45e49'
    filename = 'text_file.txt'
    unified_changes = git2net.get_unified_changes(repo_string, commit_hash, filename)
    expected_code = ['A0', 'B1', 'B2', 'B3', 'A1', 'C2', 'C3', 'C4', 'B2', 'B3', 'B4', 'A5', 'A6',
                     'A7', 'F8', 'F9', 'F10', 'F11', 'F12', 'B8', 'B9', 'B10', 'B11', 'B12']
    assert list(unified_changes.code) == expected_code


def test_mine_git_repo(repo_string, sqlite_db_file):
    if os.path.exists(sqlite_db_file):
        os.remove(sqlite_db_file)
    git2net.mine_git_repo(repo_string, sqlite_db_file, blame_C='CCC4')
    assert True


def test_get_line_editing_paths(sqlite_db_file):
    paths, dag, node_info, edge_info = git2net.get_line_editing_paths(sqlite_db_file,
                                                                      with_start=True)
    assert len(dag.isolate_nodes()) == 0


def test_get_commit_editing_paths_1(sqlite_db_file):
    sqlite_db_file = 'tests/test_repo_1.db'

    paths, dag, node_info, edge_info = git2net.get_commit_editing_paths(sqlite_db_file)

    assert len(dag.isolate_nodes()) == 0
    assert len(dag.nodes) == 31
    assert len(dag.successors[None]) == 10


def test_get_commit_editing_paths_2(sqlite_db_file):
    time_from = datetime(2019, 2, 12, 10, 0, 0)
    time_to = datetime(2019, 2, 12, 11, 0, 0)

    paths, dag, node_info, edge_info = git2net.get_commit_editing_paths(sqlite_db_file,
                                                                        time_from=time_from,
                                                                        time_to=time_to)

    assert len(dag.isolate_nodes()) == 0
    assert len(dag.nodes) == 15
    assert len(dag.successors[None]) == 6


def test_get_commit_editing_paths_3(sqlite_db_file):
    time_from = datetime(2019, 2, 12, 11, 0, 0)
    time_to = datetime(2019, 2, 12, 12, 0, 0)
    filename = 'text_file.txt'

    paths, dag, node_info, edge_info = git2net.get_commit_editing_paths(sqlite_db_file,
                                                                        time_from=time_from,
                                                                        time_to=time_to,
                                                                        filename=filename)

    assert len(dag.isolate_nodes()) == 0
    assert len(dag.nodes) == 17
    assert len(dag.successors[None]) == 1


def test_get_coediting_network(sqlite_db_file):
    time_from = datetime(2019, 2, 12, 11, 00, 0)
    time_to = datetime(2019, 2, 12, 11, 15, 0)

    t, node_info, edge_info = git2net.get_coediting_network(sqlite_db_file, time_from=time_from,
                                                            time_to=time_to)

    expected_edges = [('Author B', 'Author A', 1549965657),
                      ('Author A', 'Author B', 1549966134),
                      ('Author B', 'Author A', 1549966184),
                      ('Author C', 'Author B', 1549966309),
                      ('Author C', 'Author A', 1549966309),
                      ('Author C', 'Author A', 1549966309),
                      ('Author B', 'Author A', 1549966356),
                      ('Author B', 'Author A', 1549965738),
                      ('Author C', 'Author A', 1549966451),
                      ('Author C', 'Author A', 1549966451),
                      ('Author C', 'Author A', 1549966451)]

    assert len(set(t.tedges).difference(set(expected_edges))) == 0


def test_get_coauthorship_network(sqlite_db_file):
    time_from = datetime(2019, 2, 12, 11, 00, 0)
    time_to = datetime(2019, 2, 12, 11, 15, 0)

    n, node_info, edge_info = git2net.get_coauthorship_network(sqlite_db_file, time_from=time_from,
                                                               time_to=time_to)

    expected_nonzero_rows = [0, 0, 1, 1, 2, 2]
    expected_nonzero_columns = [1, 2, 0, 2, 0, 1]

    assert list(n.adjacency_matrix().nonzero()[0]) == expected_nonzero_rows
    assert list(n.adjacency_matrix().nonzero()[1]) == expected_nonzero_columns


def test_get_bipartite_network(sqlite_db_file):
    time_from = datetime(2019, 2, 12, 11, 00, 0)
    time_to = datetime(2019, 2, 12, 11, 10, 0)

    t, node_info, edge_info = git2net.get_bipartite_network(sqlite_db_file, time_from=time_from,
                                                            time_to=time_to)

    expected_edges = [('Author A', 'text_file.txt', 1549965641),
    ('Author B', 'text_file.txt', 1549965657),
    ('Author A', 'text_file.txt', 1549966134),
    ('Author B', 'text_file.txt', 1549966184),
    ('Author B', 'text_file.txt', 1549965738)]

    assert len(set(t.tedges).difference(set(expected_edges))) == 0
