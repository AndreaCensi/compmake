def get_ndp():
    from mcdp_lang import parse_ndp  # ok

    return parse_ndp("mcdp {}")


def get_poset():
    from mcdp_posets import Nat  # ok

    return Nat()


def get_primitivedp():
    from mcdp_dp import Identity  # ok
    from mcdp_posets import Nat  # ok

    return Identity(Nat())


# mcdp_primitive
