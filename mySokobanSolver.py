
'''

    Sokoban assignment


The functions and classes defined in this module will be called by a marker script.
You should complete the functions and classes according to their specified interfaces.

No partial marks will be awarded for functions that do not meet the specifications
of the interfaces.

You are NOT allowed to change the defined interfaces.
In other words, you must fully adhere to the specifications of the
functions, their arguments and returned values.
Changing the interfacce of a function will likely result in a fail
for the test of your code. This is not negotiable!

You have to make sure that your code works with the files provided
(search.py and sokoban.py) as your code will be tested
with the original copies of these files.

Last modified by 2021-08-17  by f.maire@qut.edu.au
- clarifiy some comments, rename some functions
  (and hopefully didn't introduce any bug!)

'''

# You have to make sure that your code works with
# the files provided (search.py and sokoban.py) as your code will be tested
# with these files
import search
import sokoban

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def my_team():
    '''
    Return the list of the team members of this assignment submission as a list
    of triplet of the form (student_number, first_name, last_name)

    '''

    return [ (11530189, 'Stephen', 'Dang'), (11463333, 'Hieu', 'Pham'), (11588608, 'Oliver', 'Stewart') ]

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class TabooHelper:
    '''
    Helper class for computing taboo cells in a Sokoban warehouse.

    A taboo cell is any interior cell where placing a box would make the
    puzzle unsolvable.  The computation uses two rules:
      Rule 1: a non-target corner cell is taboo.
      Rule 2: all cells between two taboo corners along a wall are taboo,
              provided none of those cells is a target.
    '''

    _DIRS = {'left': (-1,0), 'right': (1,0), 'up': (0,-1), 'down': (0,1)}

    def __init__(self, warehouse):
        '''
        Initialise the helper with the static features of the warehouse.

        @param warehouse:
            a Warehouse object whose walls, targets, and worker position
            are used to determine taboo cells.
        '''
        self.walls = set(warehouse.walls)
        self.targets = set(warehouse.targets)
        self.worker = warehouse.worker
        self.max_x, self.max_y = (max(coords) for coords in zip(*self.walls))

    def is_target(self, pos):
        '''
        Return True if the given position is a target cell.

        @param pos:
            an (x, y) tuple representing the cell to test.

        @return
            True if pos is a target cell, False otherwise.
        '''
        return pos in self.targets

    def has_wall(self, pos, direction):
        '''
        Return True if the cell adjacent to pos in the given direction is a wall.

        @param pos:
            an (x, y) tuple representing the reference cell.
        @param direction:
            one of 'left', 'right', 'up', or 'down'.

        @return
            True if the neighbouring cell in that direction is a wall,
            False otherwise.
        '''
        dx, dy = self._DIRS[direction]
        return (pos[0]+dx, pos[1]+dy) in self.walls

    def neighbours(self, pos):
        '''
        Yield the four cardinal neighbours of pos.

        @param pos:
            an (x, y) tuple representing the cell whose neighbours are needed.

        @return
            A generator yielding the (x, y) tuples for the left, right,
            up, and down neighbours of pos.
        '''
        x, y = pos
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            yield (x+dx, y+dy)

    def is_corner(self, pos):
        '''
        Return True if pos is a non-target corner cell.

        A cell is a corner if it has a wall on at least one horizontal side
        and at least one vertical side.  Target cells are never corners for
        the purpose of taboo detection.

        @param pos:
            an (x, y) tuple representing the cell to test.

        @return
            True if pos is a non-target corner, False otherwise.
        '''
        if self.is_target(pos):
            return False
        return (
            (self.has_wall(pos, 'left') or self.has_wall(pos, 'right')) and
            (self.has_wall(pos, 'up') or self.has_wall(pos, 'down'))
        )

    def flood_fill(self, seeds, is_passable):
        '''
        Perform a flood-fill from the given seed positions, expanding only
        into cells that satisfy is_passable.

        @param seeds:
            an iterable of (x, y) starting positions for the fill.
        @param is_passable:
            a callable that accepts an (x, y) tuple and returns True if
            that cell may be visited.

        @return
            A set of (x, y) tuples for all reachable, passable cells.
        '''
        visited = set()
        frontier = list(seeds)
        while frontier:
            current = frontier.pop()
            if current in visited or not is_passable(current):
                continue
            visited.add(current)
            frontier.extend(self.neighbours(current))
        return visited

    def mark_taboo_line(self, line_positions, make_pos, wall_side, taboo):
        '''
        Mark cells between pairs of taboo corners along a single row or column
        as taboo, provided none of the intervening cells is a target.

        @param line_positions:
            a sorted list of the varying coordinate values (x values for a row,
            y values for a column) that are candidates for marking.
        @param make_pos:
            a callable that converts a coordinate value to an (x, y) tuple for
            the current row or column.
        @param wall_side:
            the wall direction ('up', 'down', 'left', or 'right') that must be
            present at each candidate cell for it to be part of a taboo segment.
        @param taboo:
            the current set of known taboo cells, used to identify corner
            endpoints of taboo segments.

        @return
            A list of (x, y) tuples that should be added to the taboo set.
        '''
        def flush(segment):
            if len(segment) < 2:
                return []
            corners = [c for c in segment if make_pos(c) in taboo and self.has_wall(make_pos(c), wall_side)]
            return [
                make_pos(c)
                for start, end in zip(corners, corners[1:])
                if not any(self.is_target(make_pos(c)) for c in range(start + 1, end))
                for c in range(start, end + 1)
            ]
        result, segment = [], []
        for coord in line_positions:
            if segment and coord != segment[-1] + 1:
                result += flush(segment)
                segment = []
            segment.append(coord)
        return result + flush(segment)

    def compute(self):
        '''
        Compute and return the complete set of taboo cells for the warehouse.

        The method first flood-fills the interior of the warehouse from the
        worker's starting position, then applies the two taboo rules:
          Rule 1: mark all non-target interior corners as taboo.
          Rule 2: extend taboo markings along wall-adjacent rows and columns
                  between pairs of corner taboo cells.

        @return
            A set of (x, y) tuples representing all taboo cells.
        '''
        if not self.walls:
            return set()
        inside = self.flood_fill(
            [self.worker],
            lambda pos: pos not in self.walls and 0 <= pos[0] <= self.max_x and 0 <= pos[1] <= self.max_y
        )
        taboo = set(filter(self.is_corner, inside))
        for y in range(self.max_y + 1):
            row_cells = [x for x in range(self.max_x + 1) if (x, y) in inside and not self.is_target((x, y))]
            for side in ('up', 'down'):
                taboo.update(self.mark_taboo_line([x for x in row_cells if self.has_wall((x, y), side)], lambda x, y=y: (x, y), side, taboo))
        for x in range(self.max_x + 1):
            col_cells = [y for y in range(self.max_y + 1) if (x, y) in inside and not self.is_target((x, y))]
            for side in ('left', 'right'):
                taboo.update(self.mark_taboo_line([y for y in col_cells if self.has_wall((x, y), side)], lambda y, x=x: (x, y), side, taboo))
        return taboo

def taboo_cells(warehouse):
    '''
    Identify the taboo cells of a warehouse. A "taboo cell" is by definition
    a cell inside a warehouse such that whenever a box get pushed on such
    a cell then the puzzle becomes unsolvable.

    Cells outside the warehouse are not taboo. It is a fail to tag one as taboo.

    When determining the taboo cells, you must ignore all the existing boxes,
    only consider the walls and the target  cells.
    Use only the following rules to determine the taboo cells;
     Rule 1: if a cell is a corner and not a target, then it is a taboo cell.
     Rule 2: all the cells between two corners along a wall are taboo if none of
             these cells is a target.

    @param warehouse:
        a Warehouse object with a worker inside the warehouse

    @return
       A string representing the warehouse with only the wall cells marked with
       a '#' and the taboo cells marked with a 'X'.
       The returned string should NOT have marks for the worker, the targets,
       and the boxes.
    '''
    taboo = TabooHelper(warehouse).compute()
    walls = warehouse.walls
    max_x, max_y = (max(coords) for coords in zip(*walls))
    return '\n'.join(
        ''.join('#' if (x, y) in walls else 'X' if (x, y) in taboo else ' ' for x in range(max_x + 1))
        for y in range(max_y + 1)
    )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class SokobanState():
    '''
    Represents a Sokoban puzzle state.
    Stores the worker position and box positions with their weights.
    Boxes are stored as a sorted tuple of (x, y, weight) to ensure
    consistent ordering for hashing and comparison.
    '''

    def __init__(self, worker, boxes, warehouse=None):
        '''
        Initialise a SokobanState.

        @param worker:
            an (x, y) tuple representing the worker's position.
        @param boxes:
            an iterable of (x, y, weight) tuples, one per box.
        @param warehouse:
            the original Warehouse object used to reconstruct a Warehouse
            from this state.  May be None if to_warehouse will never be
            called without an explicit warehouse argument.
        '''
        self.worker = worker
        self.boxes = tuple(sorted(boxes))
        self.initial_warehouse = warehouse

    @classmethod
    def from_warehouse(cls, warehouse):
        '''
        Construct the initial SokobanState directly from a Warehouse object.

        @param warehouse:
            a Warehouse object containing the starting worker position,
            box positions, and box weights.

        @return
            A SokobanState instance representing the warehouse's initial
            configuration.
        '''
        worker = warehouse.worker
        boxes = [(x, y, w) for (x, y), w in zip(warehouse.boxes, warehouse.weights)]
        return cls(worker, boxes, warehouse)

    def to_warehouse(self, initial_warehouse=None):
        '''
        Reconstruct a Warehouse object from this state.

        @param initial_warehouse:
            an optional Warehouse object to use as the base for reconstruction.
            If None, self.initial_warehouse is used instead.

        @return
            A Warehouse object reflecting the worker and box positions stored
            in this state.
        '''
        warehouse = self.initial_warehouse if initial_warehouse is None else initial_warehouse

        if warehouse is None:
            raise ValueError("initial_warehouse is required if SokobanState isn't initialised with a warehouse")

        return warehouse.copy(
            worker=self.worker,
            boxes=tuple((x, y) for x, y, _ in self.boxes),
            weights=tuple(w for _, _, w in self.boxes)
        )

    @property
    def box_positions(self):
        '''
        Return the (x, y) positions of all boxes as a set.

        @return
            A set of (x, y) tuples, one for each box in this state.
        '''
        return set((x, y) for x, y, _ in self.boxes)

    @property
    def box_weights(self):
        '''
        Return a mapping from each box position to its weight.

        @return
            A dict mapping (x, y) tuples to integer weights for all boxes
            in this state.
        '''
        return {(x, y): w for x, y, w in self.boxes}

    def __eq__(self, other):
        '''
        Return True if other represents the same puzzle state.

        @param other:
            the object to compare against.

        @return
            True if other is a SokobanState with the same worker position
            and box configuration, False otherwise.
        '''
        return isinstance(other, SokobanState) and \
               self.worker == other.worker and \
               self.boxes == other.boxes

    def __hash__(self):
        '''
        Return a hash of this state based on the worker position and boxes.

        @return
            An integer hash value suitable for use in sets and as a dict key.
        '''
        return hash((self.worker, self.boxes))

    def __lt__(self, other):
        '''
        Return True if this state is less than other, for use in priority queues.

        Comparison is performed lexicographically on (worker, boxes).

        @param other:
            another SokobanState to compare against.

        @return
            True if (self.worker, self.boxes) < (other.worker, other.boxes).
        '''
        return (self.worker, self.boxes) < (other.worker, other.boxes)

    def __repr__(self):
        '''
        Return a developer-readable string representation of this state.

        @return
            A string of the form
            "SokobanState(worker=..., boxes=...)".
        '''
        return f"SokobanState(worker={self.worker}, boxes={self.boxes})"

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class SokobanPuzzle(search.Problem):
    '''
    An instance of the class 'SokobanPuzzle' represents a Sokoban puzzle.
    An instance contains information about the walls, the targets, the boxes
    and the worker.

    Your implementation should be fully compatible with the search functions of
    the provided module 'search.py'.

    '''

    #
    #         "INSERT YOUR CODE HERE"
    #
    #     Revisit the sliding puzzle and the pancake puzzle for inspiration!
    #
    #     Note that you will need to add several functions to
    #     complete this class. For example, a 'result' method is needed
    #     to satisfy the interface of 'search.Problem'.
    #
    #     You are allowed (and encouraged) to use auxiliary functions and classes


    def __init__(self, warehouse):
        '''
        Initialise the SokobanPuzzle from a Warehouse object.

        Precomputes the set of wall cells, target cells, and taboo cells for
        fast lookup during search, then constructs the initial SokobanState.

        @param warehouse:
            a valid Warehouse object representing the puzzle to solve.
        '''
        self.warehouse = warehouse

        # storing static data as sets for fast lookup
        self.walls = set(warehouse.walls)
        self.targets = set(warehouse.targets)
        self.taboo_cells = TabooHelper(warehouse).compute()

        self.possible_actions = {
            'Left': (-1, 0),
            'Right': (1, 0),
            'Up': (0, -1),
            'Down': (0, 1)
        }

        initial = SokobanState.from_warehouse(warehouse)

        super().__init__(initial=initial)

    def actions(self, state, ignore_taboo_cells=False):
        '''
        Return the list of actions that can be executed in the given state.

        An action is valid if the worker can move in that direction without
        walking into a wall, and if a box is pushed, the destination cell
        for that box must not be a wall, another box, or (unless
        ignore_taboo_cells is True) a taboo cell.

        @param state:
            the current SokobanState.
        @param ignore_taboo_cells:
            if True, boxes may be pushed onto taboo cells.  Defaults to False.

        @return
            A list of action strings (subsets of 'Left', 'Right', 'Up', 'Down')
            that are legal in the given state.
        '''

        # copy state into worker position and box positions
        valid_actions = []

        for action, (dx, dy) in self.possible_actions.items():
            # calculate new worker position
            new_worker = (state.worker[0] + dx, state.worker[1] + dy)

            # check if worker is moving to an empty cell
            if new_worker not in self.walls and new_worker not in state.box_positions:
                valid_actions.append(action)
                continue

            # check cell beyond box if pushing
            if new_worker in state.box_positions:
                new_box = (new_worker[0] + dx, new_worker[1] + dy)

                # check if the new box's position is valid
                if new_box not in (self.walls | state.box_positions | (set() if ignore_taboo_cells else self.taboo_cells)):
                    valid_actions.append(action)

        return valid_actions

    def result(self, state, action):
        '''
        Return the state that results from executing the given action.

        The action must be one of the actions returned by self.actions(state).
        If the worker moves into a box, that box is pushed one cell further
        in the same direction.

        @param state:
            the current SokobanState.
        @param action:
            one of 'Left', 'Right', 'Up', or 'Down'.

        @return
            A new SokobanState reflecting the worker's move and any box push.
        '''
        worker_x, worker_y = state.worker
        box_positions = state.box_positions

        dx, dy = self.possible_actions[action]
        new_worker = (worker_x + dx, worker_y + dy)

        # build new boxes, moving the pushed box if any
        new_boxes = set(state.boxes)
        if new_worker in box_positions:
            new_box = (new_worker[0] + dx, new_worker[1] + dy)
            # find and replace the pushed box entry (preserving its weight)
            pushed = next(b for b in new_boxes if (b[0], b[1]) == new_worker)
            new_boxes.remove(pushed)
            new_boxes.add((new_box[0], new_box[1], pushed[2]))

        return SokobanState(new_worker, new_boxes, state.initial_warehouse)

    def goal_test(self, state):
        '''
        Return True if every box is positioned on a target cell.

        @param state:
            the SokobanState to test.

        @return
            True if the set of box positions equals the set of target
            positions, False otherwise.
        '''
        return state.box_positions == self.targets

    def path_cost(self, c, state1, action, state2):
        '''
        Return the cost of a solution path that arrives at state2 from
        state1 via action, assuming cost c to get up to state1.

        Each step costs 1.  If a box was pushed, an additional cost equal
        to that box's weight is added.

        @param c:
            the cost accumulated to reach state1.
        @param state1:
            the state before the action.
        @param action:
            the action taken (one of 'Left', 'Right', 'Up', 'Down').
        @param state2:
            the state after the action.

        @return
            The total path cost to reach state2.
        '''
        moved = state1.box_positions - state2.box_positions

        # no box pushed
        if not moved:
            return c + 1

        origin = next(iter(moved))
        weight = state1.box_weights[origin]

        return c + 1 + weight

    def value(self, state):
        '''
        Return a value estimate for the given state, used by hill-climbing
        and related optimisation algorithms.

        The value is the negated sum of (Manhattan distance to nearest target
        multiplied by box weight) for all boxes not yet on a target.  A higher
        value indicates a state closer to the goal.

        @param state:
            the SokobanState to evaluate.

        @return
            A non-positive integer representing the estimated remaining cost,
            negated so that higher values are better.
        '''
        total = 0

        for pos in state.box_positions:
            if pos in self.targets:
                continue
            distance = min(abs(pos[0] - t[0]) + abs(pos[1] - t[1]) for t in self.targets)
            total -= distance * state.box_weights[pos]

        return total

    def h(self, node):
        '''
        Heuristic estimate of the cost from node to the goal, for use with
        A* search.

        Returns the negated value of the node's state, which approximates
        the remaining push cost as the sum of weighted Manhattan distances
        from each box to its nearest target.

        @param node:
            a search Node whose state is a SokobanState.

        @return
            A non-negative number estimating the cost to reach the goal.
        '''
        return -self.value(node.state)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def check_elem_action_seq(warehouse, action_seq):
    '''

    Determine if the sequence of actions listed in 'action_seq' is legal or not.

    Important notes:
      - a legal sequence of actions does not necessarily solve the puzzle.
      - an action is legal even if it pushes a box onto a taboo cell.

    @param warehouse: a valid Warehouse object

    @param action_seq: a sequence of legal actions.
           For example, ['Left', 'Down', Down','Right', 'Up', 'Down']

    @return
        The string 'Impossible', if one of the action was not valid.
           For example, if the agent tries to push two boxes at the same time,
                        or push a box into a wall.
        Otherwise, if all actions were successful, return
               A string representing the state of the puzzle after applying
               the sequence of actions.  This must be the same string as the
               string returned by the method  Warehouse.__str__()
    '''

    puzzle = SokobanPuzzle(warehouse=warehouse)
    state = puzzle.initial

    for action in action_seq:
        if not action in puzzle.actions(state, ignore_taboo_cells=True):
            return 'Impossible'
        state = puzzle.result(state, action)

    return state.to_warehouse().__str__()

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def solve_weighted_sokoban(warehouse):
    '''
    This function analyses the given warehouse.
    It returns the two items. The first item is an action sequence solution.
    The second item is the total cost of this action sequence.

    @param
     warehouse: a valid Warehouse object

    @return

        If puzzle cannot be solved
            return 'Impossible', None

        If a solution was found,
            return S, C
            where S is a list of actions that solves
            the given puzzle coded with 'Left', 'Right', 'Up', 'Down'
            For example, ['Left', 'Down', Down','Right', 'Up', 'Down']
            If the puzzle is already in a goal state, simply return []
            C is the total cost of the action sequence C

    '''

    puzzle = SokobanPuzzle(warehouse)

    if puzzle.goal_test(puzzle.initial):
        return [], 0

    solution = search.astar_graph_search(puzzle, puzzle.h)

    if solution is None:
        return 'Impossible', None

    action_seq = solution.solution()

    cost = solution.path_cost

    return action_seq, cost

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
