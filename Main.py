import tkinter as tk
from tkinter import scrolledtext, filedialog
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import code
import sys
import io
import networkx as nx
import matplotlib.pyplot as plt
from sympy import symbols, sympify, simplify, latex
import itertools

class CustomIO(io.StringIO):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget

    def write(self, s):
        super().write(s)
        self.widget.configure(state=tk.NORMAL)
        self.widget.insert(tk.END, s)
        self.widget.configure(state=tk.DISABLED)
        self.widget.see(tk.END)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Control system simplifier')
        self.state('zoomed')
        self.G = nx.DiGraph()
        self.main_frame = tk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.menu_frame = tk.Frame(self.main_frame, height=400, bg='lightgray')
        self.menu_frame.pack(side=tk.TOP, fill=tk.BOTH)
        self.create_menu()

        self.console_frame = tk.Frame(self.main_frame, width=400, bg='lightgray')
        self.console_frame.pack(side=tk.LEFT, fill=tk.BOTH)
        self.execute_just_once()

        self.graph_frame = tk.Frame(self.main_frame, bg='white')
        self.graph_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.main_frame.paneconfig(self.console_frame, minsize=350)
        self.main_frame.paneconfig(self.graph_frame, minsize=900)

        self.output_area = scrolledtext.ScrolledText(self.console_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.output_area.pack(expand=True, fill=tk.BOTH)

        self.input_area = tk.Entry(self.console_frame)
        self.input_area.pack(fill=tk.X)
        self.input_area.bind("<Return>", self.get_commands)

        self.custom_io = CustomIO(self.output_area)
        self.local_vars = {}

        self.interpreter = code.InteractiveInterpreter(self.local_vars)

        sys.stdout = self.custom_io
        sys.stderr = self.custom_io

        self.history = []
        self.redo_history = []
        self.bind('<Control-z>', self.undo)
        self.bind('<Control-Shift-Z>', self.redo)

    def create_menu(self):
        menu_bar = tk.Menu(self)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Open", command=self.load_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menu_bar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menu_bar, tearoff=0)
        edit_menu.add_command(label="Undo (Ctrl + z)", command=self.undo)
        edit_menu.add_command(label="Redo (Ctrl + Shift + z)", command=self.redo)
        menu_bar.add_cascade(label="Edit", menu=edit_menu)

        edit_menu = tk.Menu(menu_bar, tearoff=0)
        edit_menu.add_command(label="System transfer function", command=self.Mason)
        edit_menu.add_command(label="Delete graph", command=self.delete_graph)
        menu_bar.add_cascade(label="Graph", menu=edit_menu)

        self.config(menu=menu_bar)
        
    def execute_just_once(self):
        self.Coords = {'start' : (0, 0), 'end' : (1, 0)}
        self.lista = [['start', 0], ['end', 1]]
        self.G = nx.DiGraph()
        self.G.add_node('start', index=0)
        self.G.add_node('end', index=1)
        x = symbols('x')
        s = symbols('s')

    def undo(self, event=None):
        if self.history:
            self.redo_history.append(self.G.copy())
            self.G = self.history.pop()
            self.draw()

    def redo(self, event=None):
        if self.redo_history:
            self.history.append(self.G.copy())
            self.G = self.redo_history.pop()
            self.draw()

    def get_commands(self, event=None):
        commands = self.input_area.get()
        self.input_area.delete(0, tk.END)
        self.output_area.configure(state=tk.NORMAL)
        
        for command in commands.split('\n'):
            if command.strip():
                self.output_area.insert(tk.END, f'>>> {command}\n')
                self.execute_command(command)

        self.output_area.configure(state=tk.DISABLED)
        self.output_area.see(tk.END)

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[('Text Files', '*.txt')])
        if file_path:
            with open(file_path, 'r') as file:
                commands = file.read()
                self.output_area.configure(state=tk.NORMAL)
                for command in commands.split('\n'):
                    if command.strip():  # Only execute non-empty lines
                        self.output_area.insert(tk.END, f">>> {command}\n")
                        self.execute_command(command)
                self.output_area.configure(state=tk.DISABLED)
                self.output_area.see(tk.END)
    
    def clear_console(self):
        self.output_area.configure(state=tk.NORMAL)
        self.output_area.delete(1.0, tk.END)
        self.output_area.configure(state=tk.DISABLED)

    def delete_graph(self):
        self.Coords = {'start' : (0, 0), 'end' : (1, 0)}
        self.lista = [['start', 0], ['end', 1]]
        self.G = nx.DiGraph()
        self.G.add_node('start', index=0)
        self.G.add_node('end', index=1)
        self.draw()

    def draw(self):
        for widget in self.graph_frame.winfo_children():
            widget.destroy()

        plt.close('all')

        self.fig, self.ax = plt.subplots()
        for indice, sublista in enumerate(self.lista):
            self.Coords[sublista[0]] = (sublista[1], 0)
            self.G.nodes[sublista[0]]['index'] = sublista[1]

        nx.draw(self.G, pos=self.Coords, with_labels=True, edgelist=[], ax=self.ax)
                    
        for node in self.G.nodes():
            nodePos = tuple((self.G.nodes[node]['index'], 0))
            successors = list(self.G.successors(node))

            for successor in successors: # Barrido de nodos sucesores
                successorPos = tuple((self.G.nodes[successor]['index'], 0)) # Posición del sucesor iterado
                newPos = {node : nodePos, successor : successorPos}

                if self.G.has_edge(node, successor) and (self.G.nodes[successor]['index'] - self.G.nodes[node]['index']) == 1:
                    nx.draw_networkx_edges(self.G, newPos, edgelist=[(node, successor)], connectionstyle='arc3,rad=0', ax=self.ax) # linea nodo a sucesor
                    
                
                if self.G.has_edge(node, successor) and (self.G.nodes[successor]['index'] - self.G.nodes[node]['index']) > 1:
                    nx.draw_networkx_edges(self.G, newPos, edgelist=[(node, successor)], connectionstyle='arc3,rad=-0.5', ax=self.ax) # linea sucesor a nodo
                    
                
                if self.G.has_edge(node, successor) and (self.G.nodes[successor]['index'] - self.G.nodes[node]['index']) < 1:
                    nx.draw_networkx_edges(self.G, newPos, edgelist=[(node, successor)], connectionstyle='arc3,rad=-0.5', ax=self.ax) # linea sucesor a nodo

        self.annotation = self.ax.annotate(
            text='',
            xy=(0, 0),
            xytext=(15, 15), # distance from x, y
            textcoords='offset points',
            bbox={'boxstyle': 'round', 'fc': 'w'},
            arrowprops={'arrowstyle': '->'}
        )
        self.annotation.set_visible(False)

        self.fig.canvas.mpl_connect('motion_notify_event', self.motion_hover)

        canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        canvas.draw()

        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.graph_frame.update()

    def closer_node(self, x, y):
        nodo_mas_cercano = None
        distancia_minima = float('inf')

        for nodo, coords in self.Coords.items():
            x_nodo, y_nodo = self.Coords[nodo]
            distancia = ((x - x_nodo)**2 + (y - y_nodo)**2)**(1/2)
            if distancia < distancia_minima:
                distancia_minima = distancia
                nodo_mas_cercano = nodo

        return nodo_mas_cercano

    def motion_hover(self, event):
        annotation_visibility = self.annotation.get_visible()
        if event.inaxes == self.ax:
            x, y = event.xdata, event.ydata
            node_index = self.closer_node(x, y)
            edges = self.G.edges(node_index, data=True)

            if len(edges) > 0:
                text_label = ''
                for u, v, data in edges:
                    weight = data['weight']
                    weight_latex = latex(weight)
                    text_label += f'Edge ({u}, {v}): ${weight_latex}$\n'
                    
                self.annotation.xy = self.Coords[node_index]
                self.annotation.set_text(text_label.strip())
                self.annotation.set_alpha(0.9)
                self.annotation.set_visible(True)
                self.fig.canvas.draw_idle()
            else:
                if annotation_visibility:
                    self.annotation.set_visible(False)
                    self.fig.canvas.draw_idle()
        else:
            if annotation_visibility:
                self.annotation.set_visible(False)
                self.fig.canvas.draw_idle()

    def path_gain(self, G, path):
        total_gain = 1
        for i in range(len(path) - 1):
            node = path[i]
            next_node = path[i + 1]
            if self.G.has_edge(node, next_node):
                gain_edge = G[node][next_node]['weight']
                total_gain *= gain_edge
        return total_gain

    def loop_gain(self, G, path):
        path.append(path[0])
        total_gain = 1
        for i in range(len(path) - 1):
            node = path[i]
            next_node = path[i + 1]
            if self.G.has_edge(node, next_node):
                gain_edge = G[node][next_node]['weight']
                total_gain *= gain_edge
        path.pop()
        return total_gain

    def non_touching_loops(self, loops, n):
        combinaciones = []
        for comb in itertools.combinations(loops, n):
            nodos_comb = set().union(*comb)
            if len(nodos_comb) == sum(len(loop) for loop in comb):
                combinaciones.append(comb) # Convertir la tupla a lista
        return combinaciones
        
    def get_determinant(self, G):
        loop_paths = list(nx.simple_cycles(G))
        loops = {}
        individual_loop_gains = []
        for loop in loop_paths:
            loops[f'{loop}'] = self.loop_gain(G, loop)
            individual_loop_gains.append(self.loop_gain(G, loop))

        loop_combinations = []
        for i in range(len(loop_paths)):
            loop_combinations.append(self.non_touching_loops(loop_paths, i+2))
            if len(loop_combinations[i]) == 0:
                loop_combinations.pop()
                break

        gain = 1
        simple_loop_gains = []
        total_loop_gains = []
        for i in range(len(loop_combinations)):
            simple_loop_gains = []
            for j in range(len(loop_combinations[i])):
                for k in range(len(loop_combinations[i][j])):
                    gain *= loops[f'{loop_combinations[i][j][k]}']
                
                simple_loop_gains.append(gain)
                gain = 1
            total_loop_gains.append(simple_loop_gains)
        
        total_loop_gains.insert(0, individual_loop_gains)

        determinant = 1
        for i in range(len(total_loop_gains)):
            determinant += (-1)**(i+1) * sum(total_loop_gains[i])
        
        return simplify(determinant)

    def add_node_to_list(self, lista, node):
        posicion = node[1]
        index = 0
        for i, nodo in enumerate(lista):
            if nodo[1] < posicion:
                index = i + 1
        lista.insert(index, node)
        
        for i, nodo in enumerate(lista):
            nodo[1] = i
        
        return lista
    
    def update_list(self):
        nuevo_valor = 1
        nueva_lista = []
        
        for elemento in self.lista:
            if elemento[1] != nuevo_valor:
                nueva_lista.append((elemento[0], nuevo_valor))
            nuevo_valor += 1
        
        self.lista = nueva_lista

    def Mason(self):
        try:
            determinante = self.get_determinant(self.G)
            
            forward_paths = list(nx.all_simple_paths(self.G, source='start', target='end'))
            if len(forward_paths) == 0:
                raise Exception('There aren\'t valid paths between \'start\' and \'end\'')
            paths = {}
            determinants = {}
            mason_gain = 0
            for path in forward_paths:
                paths[f'{path}'] = self.path_gain(self.G, path)
                H = self.G.copy()
                H.remove_nodes_from(path)
                determinants[f'{path}'] = self.get_determinant(H)

                mason_gain += (paths[f'{path}']*determinants[f'{path}'])/determinante
            self.mason_gain = simplify(mason_gain)
            print(f'{self.mason_gain}')
        except Exception as e:
            print(f'Error: {e}')

    def execute_command(self, command):
        x = symbols('x')
        s = symbols('s')
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        try:
            sys.stdout = self.custom_io
            sys.stderr = self.custom_io
        except Exception as e:
            self.output_area.insert(tk.END, f"{e}\n")
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        
        if 'exit' in command:
            try:
                self.destroy()
            except Exception as e:
                pass

        elif command.strip() == "clear":
            self.clear_console()
            return
        
        elif 'system transfer function' in command:
            self.Mason()

        elif 'delete signal:' in command:
            try:
                self.history.append(self.G.copy())
                self.redo_history = []

                node_name = list(eval(command[15:]))
                node_name = str(node_name[0])
                for nodo in self.lista:
                    if nodo[0] == node_name:
                        self.G.remove_node(nodo[0])
                        self.lista.remove(nodo)
                self.draw()
                
            except Exception as e:
                print(f'Error: {e}')

        elif 'delete function:' in command:
            try:
                self.history.append(self.G.copy())
                self.redo_history = []
                InputList = eval(command[16:])
                self.G.remove_edge(InputList[0], InputList[1])
                self.draw()

            except Exception as e:
                print(f'Error: {e}')

        elif 'signal:' in command:
            try:
                self.history.append(self.G.copy())
                self.redo_history = []
                InputList = eval(command[8:])
                node_name = str(InputList[0])
                index = int(InputList[1])
                if index == 0:
                    index = 1
                elif index > len(self.Coords) - 1:
                    index = len(self.Coords) - 1
                self.lista = self.add_node_to_list(self.lista, [node_name, index])

                for indice, sublista in enumerate(self.lista):
                    self.Coords[sublista[0]] = (sublista[1], 0)
                    if node_name in sublista:
                        self.G.add_node(node_name, index=sublista[1])
                self.draw()
            except Exception as e:
                print(f'Error: {e}')

        elif 'function:' in command:
            try:
                self.history.append(self.G.copy())
                self.redo_history = []
                InputList = eval(command[10:])
                function = simplify(sympify(InputList[2]))
                if self.G.has_node(str(InputList[0])) and self.G.has_node(str(InputList[1])):
                    self.G.add_edge(str(InputList[0]), str(InputList[1]), weight=function)
                    self.draw()
                else:
                    raise Exception('Invalid signal(s)')
            except Exception as e:
                print(f'Error: {e}')

        elif 'draw' in command:
            self.draw()

        elif 'delete graph' in command:
            self.delete_graph()

if __name__ == "__main__":
    app = App()
    app.mainloop()
