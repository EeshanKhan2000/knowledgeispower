"""Protein representation modules (Amendment 9): one module per knowledge source, each exposing
``block(var_names, d)`` (p x (d+1) feature matrix with a final 0/1 has-data column) and, where the
source is relational, ``graph(var_names)`` (networkx.Graph over the var_names strings).
"""
