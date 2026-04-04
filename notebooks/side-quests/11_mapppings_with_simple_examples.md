## Dictionary of primitives

This table gives the same underlying ideas in four languages:
three-phase / sequence systems, Hilbert / polarization language, graph / gauge / coloring language, and a child-friendly toy picture.

| Primitive                          | Three-phase / sequence                                                               | Hilbert / polarization                 | Graph / gauge / coloring               | For a child                            |
| ---------------------------------- | ------------------------------------------------------------------------------------ | -------------------------------------- | -------------------------------------- | -------------------------------------- |
| **State space**                    | Balanced abc plane; ((V^+,V^-)) state                                                | State vector space                     | Faces, vertices, edges with labels     | A playground of allowed moves          |
| **Linearity / superposition**      | Balanced signals add                                                                 | States superpose                       | Flows / cochains add                   | Two slinky waves combining             |
| **Constraint subspace**            | (a+b+c=0); zero-sequence removed                                                     | Allowed physical subspace              | Admissible / flat assignments          | A train stuck on tracks                |
| **Basis / coordinates**            | abc, (\alpha\beta), dq, sequence basis                                               | Computational or rotated basis         | Face colors, edge labels               | Different ways to describe one place   |
| **Inner product / overlap**        | Metric / power-like overlap                                                          | (\langle \phi,\psi\rangle)             | Pairing of local data                  | How well two shapes line up            |
| **Norm / size**                    | Energy, (\alpha^2+\beta^2), magnitude                                                | (|\psi|^2)                             | Conserved flow size                    | How big the wiggle is                  |
| **Orthogonality**                  | (\alpha) vs (\beta); decoupled modes                                                 | Orthogonal states                      | Independent channels                   | Up-down versus left-right              |
| **Rotation / complex structure**   | Positive/negative sequence rotation                                                  | Complex phase; unitary rotation        | Oriented transport                     | A spinning top or Beyblade             |
| **Symmetry**                       | Three-phase cyclic symmetry                                                          | Rotational / unitary symmetry          | Graph or gauge symmetry                | A snowflake or pizza pattern           |
| **Mode decomposition**             | (+), (−), (0) components                                                             | Eigenmodes / spectral modes            | Cut / cycle / label classes            | Sorting toys into bins                 |
| **Projection / analyzer**          | Clarke/Park projection; recombiner                                                   | Projector / analyzer                   | Local readout across an edge           | Flashlight and shadow                  |
| **Change of basis**                | abc (\leftrightarrow) (\alpha\beta0) (\leftrightarrow) dq (\leftrightarrow) sequence | Rotate basis                           | Relabel / gauge transform              | Turning the map, not the world         |
| **Relative phase / angle**         | Electrical angle; sequence phase                                                     | Relative phase; Bloch angle            | Loop / transport phase                 | Two clocks or two swings               |
| **Local transition rule**          | Stage-by-stage propagation                                                           | Local state update                     | Edge increment (g_e)                   | Follow the next arrow                  |
| **Global consistency / closure**   | Network / phase closure                                                              | Consistent global assignment           | Zero holonomy; path independence       | Train tracks that must close           |
| **Gauge / representation freedom** | Reference angle or frame choice                                                      | Global phase convention                | Base choice / coboundary shift         | Same thing, different naming           |
| **Observable**                     | Voltage, current, power, contrast                                                    | Detector intensity / expectation       | Color difference / loop sum            | What you can actually notice           |
| **Normalization / quotienting**    | Keep direction, ignore scale                                                         | Rays / projective states               | Classes modulo relabeling              | Only care where the arrow points       |
| **Discrete readout**               | Threshold / winner-take-all                                                          | Click / binary outcome                 | Color class / parity class             | Shape sorter click                     |
| **Two-bit / four-class structure** | Two reduced coordinates; four coarse sectors                                         | Four classes from two binary questions | (V_4=\mathbb Z_2^2)                    | Two coin flips                         |
| **Circle / sphere picture**        | Normalized (\alpha\beta) circle; lifted sphere views                                 | Bloch sphere / projective sphere       | Spherical / planar map view            | Beach ball, globe, clock face          |
| **Dynamics**                       | Resonant exchange; frame motion                                                      | State evolution                        | Iterated transport / update            | Marble run or moving swing             |
| **Conservation / invariant**       | Energy; balanced-subspace preservation                                               | Norm conservation                      | Flow / cycle invariant                 | Same water in different cups           |
| **Correlation law**                | Angle-dependent contrast                                                             | Overlap-based correlation              | Compatibility statistics               | Two gears turning together             |
| **Shared preparation**             | Same source feeding branches                                                         | Jointly prepared state                 | Common assignment origin               | Two tops from one launcher             |
| **Handedness**                     | Positive vs negative sequence                                                        | Opposite helicity / rotation sense     | Opposite orientation class             | Clockwise vs counterclockwise spin     |
| **Coherence / synchronization**    | Locked phase relation                                                                | Coherent phase relation                | Consistent transport                   | Grandfather clocks in sync             |
| **Obstruction / failure mode**     | Unbalance, leakage, dissipation                                                      | Decoherence / incompatibility          | Nonzero holonomy / impossible coloring | Knot in the rope, missing puzzle piece |

### Core takeaway

Across all four languages, the recurring backbone is:

* **linear state space**
* **constraint**
* **symmetry**
* **overlap geometry**
* **projection**
* **local transition**
* **global closure**
* **discrete readout**

### Minimal toy kit

If you want a compact child-facing set of objects to reuse throughout:

* **Slinky** — superposition and propagation
* **Top / Beyblade** — spin, handedness, shared preparation
* **Clock / swings / grandfather clock** — phase and synchronization
* **Flashlight and shadow** — projection and analyzer choice
* **Shape sorter** — discrete readout
* **Train tracks / puzzle border** — closure and consistency
* **Beach ball / globe** — direction-state geometry
* **Gears** — correlation and coupling

### One-line summary

The shared structure is not “three-phase is quantum” or “coloring is circuits,” but a common skeleton of **linearity + symmetry + projection + closure** expressed in different languages.
