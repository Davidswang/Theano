
import time
import unittest

from theano.gof import Variable, Op
from theano import gof

from theano.scalar import *

from theano import tensor
from theano.tensor.elemwise import *
from theano.tests import unittest_tools


def Env(i, o):
    e = gof.Env(i, o)
    return e

class test_DimShuffle(unittest.TestCase):

    def with_linker(self, linker):
        for xsh, shuffle, zsh in [((2, 3), (1, 'x', 0), (3, 1, 2)),
                                  ((1, 2, 3), (1, 2), (2, 3)),
                                  ((1, 2, 1, 3), (1, 3), (2, 3)),
                                  ((2, 3, 4), (2, 1, 0), (4, 3, 2)),
                                  ((2, 3, 4), ('x', 2, 1, 0, 'x'), (1, 4, 3, 2, 1)),
                                  ((1, 4, 3, 2, 1), (3, 2, 1), (2, 3, 4)),
                                  ((1, 1, 4), (1, 2), (1, 4))]:
            ib = [(entry == 1) for entry in xsh]
            x = TensorType('float64', ib)('x')
            e = DimShuffle(ib, shuffle)(x)
            f = copy(linker).accept(Env([x], [e])).make_function()
            assert f(numpy.ones(xsh)).shape == zsh
            #test that DimShuffle.infer_shape work correctly
            x = TensorType('float64', ib)('x')
            e = DimShuffle(ib, shuffle)(x)
            f = copy(linker).accept(Env([x], [e.shape])).make_function()
            assert all(f(numpy.ones(xsh))) == all(zsh)

    def test_perform(self):
        self.with_linker(gof.PerformLinker())


class test_Broadcast(unittest.TestCase):
    def setUp(self):
        unittest_tools.seed_rng()

    def with_linker(self, linker):
        for xsh, ysh in [((3, 5), (3, 5)),
                         ((3, 5), (1, 5)),
                         ((3, 5), (3, 1)),
                         ((1, 5), (5, 1)),
                         ((1, 1), (1, 1)),
                         ((2, 3, 4, 5), (2, 3, 4, 5)),
                         ((2, 3, 4, 5), (1, 3, 1, 5)),
                         ((2, 3, 4, 5), (1, 1, 1, 1)),
                         ((), ())]:
            x = TensorType('float64', [(entry == 1) for entry in xsh])('x')
            y = TensorType('float64', [(entry == 1) for entry in ysh])('y')
            e = Elemwise(add)(x, y)
            f = copy(linker).accept(Env([x, y], [e])).make_function()
            xv = numpy.asarray(numpy.random.rand(*xsh))
            yv = numpy.asarray(numpy.random.rand(*ysh))
            zv = xv + yv

            self.failUnless((f(xv, yv) == zv).all())

            #test CAReduce.infer_shape
            #the Shape op don't implement c_code!
            if isinstance(linker,gof.PerformLinker):
                x = TensorType('float64', [(entry == 1) for entry in xsh])('x')
                y = TensorType('float64', [(entry == 1) for entry in ysh])('y')
                e = Elemwise(add)(x, y)
                f = copy(linker).accept(Env([x, y], [e.shape])).make_function()
                assert tuple(f(xv, yv))==tuple(zv.shape)

    def with_linker_inplace(self, linker):
        for xsh, ysh in [((5, 5), (5, 5)),
                         ((5, 5), (1, 5)),
                         ((5, 5), (5, 1)),
                         ((1, 1), (1, 1)),
                         ((2, 3, 4, 5), (2, 3, 4, 5)),
                         ((2, 3, 4, 5), (1, 3, 1, 5)),
                         ((2, 3, 4, 5), (1, 1, 1, 1)),
                         ((), ())]:
            x = TensorType('float64', [(entry == 1) for entry in xsh])('x')
            y = TensorType('float64', [(entry == 1) for entry in ysh])('y')
            e = Elemwise(Add(transfer_type(0)), {0:0})(x, y)
            f = copy(linker).accept(Env([x, y], [e])).make_function()
            xv = numpy.asarray(numpy.random.rand(*xsh))
            yv = numpy.asarray(numpy.random.rand(*ysh))
            zv = xv + yv

            f(xv, yv)

            self.failUnless((xv == zv).all())
            #test CAReduce.infer_shape
            #the Shape op don't implement c_code!
            if isinstance(linker,gof.PerformLinker):
                x = TensorType('float64', [(entry == 1) for entry in xsh])('x')
                y = TensorType('float64', [(entry == 1) for entry in ysh])('y')
                e = Elemwise(Add(transfer_type(0)), {0:0})(x, y)
                f = copy(linker).accept(Env([x, y], [e.shape])).make_function()
                xv = numpy.asarray(numpy.random.rand(*xsh))
                yv = numpy.asarray(numpy.random.rand(*ysh))
                zv = xv + yv
                
                f(xv, yv)
                
                assert xv.shape==zv.shape

    def test_perform(self):
        self.with_linker(gof.PerformLinker())

    def test_c(self):
        self.with_linker(gof.CLinker())

    def test_perform_inplace(self):
        self.with_linker_inplace(gof.PerformLinker())

    def test_c_inplace(self):
        self.with_linker_inplace(gof.CLinker())

    def test_fill(self):
        x = TensorType('float64', [0, 0])('x')
        y = TensorType('float64', [1, 1])('y')
        e = Elemwise(Second(transfer_type(0)), {0:0})(x, y)
        f = gof.CLinker().accept(Env([x, y], [e])).make_function()
        xv = numpy.ones((5, 5))
        yv = numpy.random.rand(1, 1)
        f(xv, yv)
        assert (xv == yv).all()

    def test_weird_strides(self):
        x = TensorType('float64', [0, 0, 0, 0, 0])('x')
        y = TensorType('float64', [0, 0, 0, 0, 0])('y')
        e = Elemwise(add)(x, y)
        f = gof.CLinker().accept(Env([x, y], [e])).make_function()
        xv = numpy.random.rand(2, 2, 2, 2, 2)
        yv = numpy.random.rand(2, 2, 2, 2, 2).transpose(4, 0, 3, 1, 2)
        zv = xv + yv
        assert (f(xv, yv) == zv).all()

    def test_same_inputs(self):
        x = TensorType('float64', [0, 0])('x')
        e = Elemwise(add)(x, x)
        f = gof.CLinker().accept(Env([x], [e])).make_function()
        xv = numpy.random.rand(2, 2)
        zv = xv + xv
        assert (f(xv) == zv).all()


class test_CAReduce(unittest.TestCase):
    def setUp(self):
        unittest_tools.seed_rng()

    def with_linker(self, linker, scalar_op = add):
        for xsh, tosum in [((5, 6), None),
                           ((5, 6), (0, 1)),
                           ((5, 6), (0, )),
                           ((5, 6), (1, )),
                           ((5, 6), (-1, )),
                           ((5, 6), (-2, )),
                           ((5, 6), ()),
                           ((2, 3, 4, 5), (0, 1, 3)),
                           ((2, 3, 4, 5), (-2, -3)),
                           ((5, 0), None),
                           ((5, 0), (0, )),
                           ((5, 0), (1, )),
                           ((5, 0), ()),
                           ((), None),
                           ((), ())]:
            x = TensorType('float64', [(entry == 1) for entry in xsh])('x')
            e = CAReduce(scalar_op, axis = tosum)(x)
            if tosum is None: tosum = range(len(xsh))
            f = copy(linker).accept(Env([x], [e])).make_function()
            xv = numpy.asarray(numpy.random.rand(*xsh))
            zv = xv
            numpy_raised = False
            if len(tosum)>1 and any([a<0 for a in tosum]):
                #In that case, we need to use the good order of axis in the reduction.
                axis2 = []
                for a in tosum:
                    if a<0: axis2.append(a+len(xsh))
                    else: axis2.append(a)
                assert len(axis2)==len(tosum)
                tosum = tuple(axis2)

            if scalar_op == add:
                for axis in reversed(sorted(tosum)):
                    zv = numpy.add.reduce(zv, axis)
            elif scalar_op == mul:
                for axis in reversed(sorted(tosum)):
                    zv = numpy.multiply.reduce(zv, axis)
            elif scalar_op == maximum:
                try:
                    for axis in reversed(sorted(tosum)):
                        zv = numpy.maximum.reduce(zv, axis)
                except ValueError:
                    numpy_raised=True
            elif scalar_op == minimum:
                try:
                    for axis in reversed(sorted(tosum)):
                        zv = numpy.minimum.reduce(zv, axis)
                except ValueError:
                    numpy_raised=True
            elif scalar_op == or_:
                for axis in reversed(sorted(tosum)):
                    zv = numpy.any(zv, axis)
            elif scalar_op == and_:
                for axis in reversed(sorted(tosum)):
                    zv = numpy.all(zv, axis)
            else:
                raise Exception("Test for CAReduce with scalar_op %s not implemented"%str(scalar_op))
            if scalar_op in [maximum,minimum] and numpy_raised:
                try:
                    f(xv)
                except ValueError:
                    pass
                else: 
                    self.fail()
            else:
                self.failUnless((numpy.abs(f(xv) - zv) < 1e-10).all())
                

            #test CAReduce.infer_shape
            #the Shape op don't implement c_code!
            if isinstance(linker,gof.PerformLinker):
                x = TensorType('float64', [(entry == 1) for entry in xsh])('x')
                e = CAReduce(scalar_op, axis = tosum)(x)
                if tosum is None: tosum = range(len(xsh))
                f = copy(linker).accept(Env([x], [e.shape])).make_function()
                if not(scalar_op in [maximum,minimum] and ((xsh==() or numpy.prod(xsh)==0))):
                    assert all(f(xv)== zv.shape)

    def test_perform(self):
        self.with_linker(gof.PerformLinker(), add)
        self.with_linker(gof.PerformLinker(), mul)
        self.with_linker(gof.PerformLinker(), maximum)
        self.with_linker(gof.PerformLinker(), minimum)
        #need other dtype then real
        #self.with_linker(gof.PerformLinker(), or_)
        #self.with_linker(gof.PerformLinker(), and_)

    def test_c(self):
        self.with_linker(gof.CLinker(), add)
        self.with_linker(gof.CLinker(), mul)
        self.with_linker(gof.CLinker(), maximum)
        self.with_linker(gof.CLinker(), minimum)

        #need other dtype then real        
        #no c_code for or_, and_
        #self.with_linker(gof.CLinker(), or_)
        #self.with_linker(gof.CLinker(), and_)


if __name__ == '__main__':
    unittest.main()
