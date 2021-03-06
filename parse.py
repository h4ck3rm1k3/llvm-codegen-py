import sys

from pllvm import *

class IRParser(object):

    def __init__(self, fileobj):
        self.f = fileobj
        self.mod = PModule()
        self.func = None
        self.block = None
        self.tmp_count = 0

    @staticmethod
    def split(s):
        args = [x.strip() for x in s.split(",")]
        return args

    @staticmethod
    def next_token(s):
        return s.split(None, 1)

    @staticmethod
    def convert_arg(arg, type=None):
        if arg[0] == "!":
            # Tags, so far just return as string
            return arg

        attrs = set()
        if type is None:
            m = re.match(r"(\[.+?\]|[0-9A-Za-z_]+) (.+)", arg)
            type, arg = m.groups()
            print m.groups()
            #type, arg = arg.split(None, 1)

            if not arg.startswith('c"') and " " in arg:
                mod, arg = arg.split(None, 1)
                if mod == "nocapture":
                    attrs.add(ATTR_NO_CAPTURE)
                else:
                    assert False, "%s: unsupported attributes" % mod

        try:
            v = int(arg)
            return PConstantInt(v, type)
        except:
            pass

        if arg[0] == "%":
            v = PTmpVariable(arg[1:], type)
        elif arg[0] == "@":
            v = PGlobalVariableRef(arg[1:], type)
        elif arg.startswith("label "):
            label = arg.split(None, 1)[1]
            assert label[0] == "%"
            v = PLabelRef(label[1:])
        elif arg.startswith('c"'):
            v = PConstantDataArray(arg, type)
        else:
            assert False, "Unknown arg syntax: " + arg
        v.attributes = attrs
        return v

    def next_tmp(self):
        t = str(self.tmp_count)
        self.tmp_count += 1
        return t

    def make_block(self, label=None, comment=None):
        if not label:
            label = self.next_tmp()
        self.block = PBasicBlock(self.func, label)
        self.block.comment = comment
        self.func.append(self.block)
        self.block.parent = self.func

    def parse(self):
        for l in self.f:
            if l[-1] == "\n":
                l = l[:-1]
            m = re.match(r"(.*?)([ \t]*;.*)?$", l)
            l = m.group(1)
            comment = m.group(2)
            if not l:
                if comment and comment.startswith("; ModuleID = "):
                    self.mod.module_id = comment
                continue

            if not self.func:
                # Global context
                if l.startswith("target "):
                    self.mod.target_info.append(l)
                elif l.startswith("!"):
                    self.mod.metadata.append(l)
                elif l.startswith("@"):
                    lhs, rhs = [x.strip() for x in l.split("=", 1)]
                    var = PGlobalVariable()
                    var.name = lhs[1:]
                    # @g = common global i32 0
                    while True:
                        lhs, new_rhs = rhs.split(None, 1)
                        if lhs in ("private", "linkonce", "weak", "common"):
                            var.linkage = lhs
                        elif lhs == "global":
                            pass
                        # TODO
                        elif lhs in ("unnamed_addr", "constant"):
                            pass
                        else:
                            break
                        rhs = new_rhs
                    val = self.convert_arg(rhs)
                    # FIXME: var.type apparently should be pointer to
                    var.type_str = var.type = val.type
                    var.initializer = val
                    self.mod.global_variables.append(var)

                elif l.startswith("define "):
                    m = re.match(r"define (?P<type>.+?) @(?P<name>.+?)\((?P<args>.*?)\)(?P<mods>.*?) \{", l)
                    assert m, "Syntax error in func definition:" + l
                    args = m.group("args")
                    if not args:
                        args = []
                    else:
                        args = [x.strip() for x in args.split(",")]
                    args = [self.convert_arg(x) for x in args]
                    self.func = PFunction(m.group("name"), m.group("type"), args)
                    mods = m.group("mods").strip().split()
                    self.func.does_not_throw = "nounwind" in mods
                    self.func.readonly = "readonly" in mods
                    self.mod.append(self.func)
                    self.func.parent = self.mod
                    continue

            else:
                # Function context
                if l == "}":
                    self.block = None
                    self.func = None
                    continue

                if l[-1] == ":":
                    self.make_block(l[:-1].strip(), comment)
                    continue

                if self.block is None:
                    self.make_block()

#                print "in: ", l.strip()
                comps = [x.strip() for x in l.split("=", 1)]
                if len(comps) == 2:
                    lhs, rhs = comps
                    assert lhs[0] == "%", l
                    lhs = lhs[1:]
                else:
                    lhs = None
                    rhs = comps[0]
                opcode, rhs = rhs.split(None, 1)
                inst = PInstruction()
                inst.name = lhs
                inst.opcode_name = opcode
                inst.comment = comment
                if opcode in ("icmp", "bricmp"):
                    pred, rhs = rhs.split(None, 1)
                    inst.predicate = pred
                elif opcode == "load":
                    h, t = rhs.split(None, 1)
                    if h == "getelementptr":
                        inst.offseted = True
                        rhs = t
                homotype = True
                if opcode in set(["load", "store", "getelementptr"]):
                    homotype = False
                if homotype:
                    type, rhs = rhs.split(None, 1)
                else:
                    type = None
                inst.type = type
                print "!", rhs
                if opcode == "phi":
                    inst.incoming_vars = []
                    while rhs.strip():
                        m = re.match(r"\[(.+?) *, *(.+?)\]( *, *)?(.*)", rhs)
                        var = m.group(1).strip()
                        label = m.group(2).strip()
                        rhs = m.group(4)
                        inst.incoming_vars.append((self.convert_arg(var, type), label[1:]))

                else:
                    if opcode == "getelementptr":
                        t, rhs2 = self.next_token(rhs)
                        print (t, rhs2)
                        if t == "inbounds":
                            inst.inbounds = True
                            rhs = rhs2
                    args = self.split(rhs)
                    if args[-1][0] == "!":
                        # TODO: make llvmpy compatible
                        inst.metadata = args[-1]
                        args = args[:-1]
                    if args[-1].startswith("align "):
                        inst.alignment = int(args[-1].split(None, 1)[1])
                        args = args[:-1]
                    args = [self.convert_arg(x, type) for x in args]
                    if opcode == "br" and len(args) == 3:
                        args = [args[0], args[2], args[1]]
                    if opcode == "bricmp":
                        args = [args[0], args[1], args[3], args[2]]
                    inst.operands = args
#                    print "out:", str(inst).strip()
                self.block.append(inst)
                inst.parent = self.block

        return self.mod


if __name__ == "__main__":
    p = IRParser(open(sys.argv[1]))
    mod = p.parse()
    IRRenderer.render(mod)
