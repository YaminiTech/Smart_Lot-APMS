# Technical Methodology: Core Algorithms (Relational 2.0)

This document outlines the formal mathematical and logical algorithms used in the **SMART LOT: Adaptive Parking Management System**. These algorithms ensure the high-fidelity perception, stable state-persistence, and optimized navigation required for modern urban infrastructure.

---

### **Algorithm 1: Geometric Occupancy Detection (IoA)**
**Goal**: To determine if a vehicle bounding box ($B$) is parked in a pre-defined ROI polygon ($P$).

1.  **Input**: Bounding Box $B = [x_{min}, y_{min}, x_{max}, y_{max}]$, ROI Polygon $P = \{(x_1, y_1), \dots, (x_n, y_n)\}$.
2.  **Step 1**: Construct a representative Polygon $P_B$ from the four coordinates of $B$.
3.  **Step 2**: Calculate the area of spatial intersection $A_{int} = \text{Area}(P_B \cap P)$.
4.  **Step 3**: Calculate the total area of the target ROI $A_{total} = \text{Area}(P)$.
5.  **Step 4**: Compute the occupancy ratio $R = \frac{A_{int}}{A_{total}}$.
6.  **Step 5**: **Logic Gate**: 
    *   If $R > \text{Threshold}$ (e.g., 0.15), set **Status = Occupied**.
    *   Else, set **Status = Empty**.
7.  **Output**: Boolean State $S \in \{0, 1\}$.

---

### **Algorithm 2: Global Site Stitching (Matrix Transformation)**
**Goal**: To align a local camera coordinate ($x, y$) into a unified "Global Site Map."

1.  **Input**: Local Coordinate $(x_L, y_L)$, Zone Offset Matrix $M_{zone} = [O_x, O_y]$.
2.  **Step 1**: Identify the source Zone $Z$ of the detection frame.
3.  **Step 2**: Retrieve the Translation Offsets $O_x$ and $O_y$ for Zone $Z$ from the SQL database.
4.  **Step 3**: Apply the transformation:
    *   $X_{Global} = x_L + O_x$
    *   $Y_{Global} = y_L + O_y$
5.  **Step 4**: Normalize the resulting coordinates to the global canvas resolution.
6.  **Output**: Global Coordinate $(X_G, Y_G)$.

---

### **Algorithm 3: Adaptive Navigation (Dijkstra’s Algorithm)**
**Goal**: To find the absolute shortest drivable path from the lot entrance to a target spot.

1.  **Input**: Graph $G(V, E)$, Source Node $v_s$ (Entrance), Set of Target Spots $T=\{t_1, \dots, t_n\}$.
2.  **Step 1**: Filter $T$ for all nodes $t_k$ where **Status = Empty**.
3.  **Step 2**: Initialize distances $d(v) = \infty$ for all $v \in V$, and $d(v_s) = 0$.
4.  **Step 3**: **Priority Queue Loop**:
    *   Select unvisited node $u$ with the minimum $d(u)$.
    *   For each neighbor $v$ of $u$:
        *   New distance $d_{new} = d(u) + \text{weight}(u, v)$.
        *   If $d_{new} < d(v)$, update $d(v) = d_{new}$ and set **Previous(v) = u**.
5.  **Step 4**: Find $t_{best} = \min(d(t_1), \dots, d(t_n))$ from the vacant set.
6.  **Step 5**: Backtrack from $t_{best}$ using the **Previous** pointers to reconstruct the optimal path.
7.  **Output**: Path $P_{opt} = \{v_s, \dots, v_{best}\}$.

---

### **Algorithm 4: Temporal State Smoothing (Stability Logic)**
**Goal**: To eliminate "status flickering" in the database caused by transient AI glitches.

1.  **Input**: New detected state $S_{new}$, State Buffer $L = [s_1, \dots, s_n]$.
2.  **Step 1**: Append $S_{new}$ to the circular buffer $L$ for the specific spot ID.
3.  **Step 2**: If the buffer is full, calculate the mode (most common state).
4.  **Step 3**: **Persistence Logic**: 
    *   If $\text{count}(\text{mode}(L)) \geq \text{Stability\_Threshold}$:
        *   Compare $\text{mode}(L)$ with current database state $S_{db}$.
        *   If $\text{mode}(L) \neq S_{db}$, trigger **Database UPSERT**.
    *   Else, **Maintain Status**.
5.  **Output**: Updated Database State.
