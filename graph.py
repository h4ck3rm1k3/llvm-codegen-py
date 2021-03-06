class IGraph(object):

    # directed = None

    def empty(self):
        "Return True if graph is empty."
        raise NotImplementedError

    def add_node(self, node):
        "Add node to a graph."
        raise NotImplementedError

    def add_edge(self, from_node, to_node):
        """Add edge between 2 nodes. If any of the nodes does not exist,
        it will be created."""
        raise NotImplementedError

    def iter_edges(self):
        "Iterate over all edges in the graph."
        raise NotImplementedError

    def iter_nodes(self):
        "Iterate over all nodes in the graph."
        raise NotImplementedError

    def neighs(self, n):
        "Return list of node's neighbors."
        raise NotImplementedError

    def degree(self, n):
        "Return node's degree, i.e. number of its neighbors."
        return len(self.neighs(n))

    def remove(self, n):
        "Remove node and all its edges from the graph."
        raise NotImplementedError

    def is_edge_based(self):
        "Return True is node-based ops like iter_nodes(), neighs() are expensive."
        raise NotImplementedError


class GraphWithNodeAttrs(IGraph):

    def __init__(self):
        self.node_attrs = {}

    def get_node_attr(self, node, attr):
        "Get node attribute (arbitrary named values attached to node)."
        return self.node_attrs.setdefault(node, {}).get(attr)

    def set_node_attr(self, node, attr, val):
        "Set node attribute (arbitrary named values attached to node)."
        self.node_attrs.setdefault(node, {})[attr] = val


class DigraphEdgeList(GraphWithNodeAttrs):

    directed = True

    def __init__(self):
        super(DigraphEdgeList, self).__init__()
        self.edge_list = set()

    @classmethod
    def from_edge_list(cls, edge_list):
        self = cls()
        for from_node, to_node in edge_list:
            self.add_edge(from_node, to_node)
        return self

    def is_edge_based(self):
        return True

    def empty(self):
        return len(self.edge_list) == 0

    def add_edge(self, from_node, to_node):
        self.edge_list.add((from_node, to_node))

    def iter_edges(self):
        return iter(self.edge_list)

    def iter_nodes(self):
        seen = set()
        for nodes in self.edge_list:
            for n in nodes:
                if n not in seen:
                    seen.add(n)
                    yield n

    def __eq__(self, other):
        return self.edge_list == other.edge_list

    def __str__(self):
        return str(self.edge_list)


class UngraphEdgeList(DigraphEdgeList):

    directed = False

    def add_edge(self, from_node, to_node):
        if from_node < to_node:
            edge = (from_node, to_node)
        else:
            edge = (to_node, from_node)
        DigraphEdgeList.add_edge(self, *edge)

    def neighs(self, n):
        "Return list of node's neighbors."
        neighs = []
        for from_node, to_node in self.edge_list:
            if from_node == n:
                neighs.append(to_node)
            elif to_node == n:
                neighs.append(from_node)
        return neighs


class DigraphAdjList(GraphWithNodeAttrs):
    "Graph representation based on adjacency (neighborhood) list for each node."

    def __init__(self):
        super(DigraphAdjList, self).__init__()
        self.neigh_list = {}

    @classmethod
    def from_neigh_list(cls, neigh_list):
        self = cls()
        for node, neighs in neigh_list.iteritems():
            self.add_node(node)
            for n in neighs:
                self.add_edge(node, n)
        return self

    def from_graph(self, graph):
        if graph.is_edge_based():
            for from_node, to_node in graph.iter_edges():
                self.add_edge(from_node, to_node)
#                neighs = self.neigh_list.get(from_node, [])
#                neighs.append(to_node)
#                self.neigh_list[from_node] = neighs
        else:
            raise NotImplementedError

    def is_edge_based(self):
        return False

    def empty(self):
        return len(self.neigh_list) == 0

    def neighs(self, n):
        "Return list of node's neighbors."
        return self.neigh_list[n]

    def succ(self, n):
        return self.neighs(n)

    def pred(self, n):
        preds = []
        for fr, to in self.iter_edges():
            if to == n:
                preds.append(fr)
        return preds

    def iter_edges(self):
        "Iterate over all edges in the graph."
        for node, neighs in self.neigh_list.iteritems():
            for neigh in neighs:
                yield (node, neigh)

    def iter_nodes(self):
        return self.neigh_list.iterkeys()

    def add_node(self, node):
        if node not in self.neigh_list:
            self.neigh_list[node] = set()

    def add_edge(self, from_node, to_node):
        self.add_node(from_node)
        self.neigh_list[from_node].add(to_node)

    def remove(self, n):
        "Remove node and all its edges from the graph."
        del self.neigh_list[n]
        for nd, neighs in self.neigh_list.iteritems():
            try:
                neighs.remove(n)
            # Exception type depends on underlying storage: [] or set()
            except (KeyError, ValueError):
                pass

    def __eq__(self, other):
        return self.neigh_list == other.neigh_list

    def __str__(self):
        return str(self.neigh_list)


class UngraphAdjList(DigraphAdjList):
    """Undirected graph using adjacency list. Implementation
    maintains edges of both direction between nodes.
    """
    def add_edge(self, from_node, to_node):
        super(UngraphAdjList, self).add_edge(from_node, to_node)
        super(UngraphAdjList, self).add_edge(to_node, from_node)
