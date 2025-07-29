import logging
from typing import List
from treelib import Tree

from api.v0_1.endpoints.service.models import FileTreeNode

logger = logging.getLogger('app')


def convert_file_tree_to_nodes(tree: Tree) -> List[FileTreeNode]:
    """
    Convert a file tree to a list of FileTreeNode objects.

    :param tree: The file tree to convert.
    :type tree: Tree
    :return: The converted file tree as a list of FileTreeNode objects.
    :rtype: List[FileTreeNode]
    """
    tree_nodes = []
    for node in tree.all_nodes():
        if node.tag != 'root':  # Skip the 'root' node
            parent = tree.parent(node.identifier)
            # If the parent is 'root', treat this node as a top-level node
            parent_id = '#' if parent is None or parent.tag == 'root' else parent.identifier
            tree_nodes.append(
                FileTreeNode(
                    id=node.identifier,
                    parent=parent_id,
                    text=node.tag,
                    li_attr={"data-id": node.identifier}
                )
            )
    return tree_nodes