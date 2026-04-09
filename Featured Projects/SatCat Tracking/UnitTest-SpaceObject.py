# -----------------------------------------------------------------------------------------------------------------------
# Development History
# -------------------
# 16 Jan 2026 - Created
# 02 Feb 2026 - Expanded tests and edge cases, added more assertions
# 05 Feb 2026 - Added tests for SpaceObjectList and additional edge cases
# 17 Feb 2026 - Replaced filterActive with filterDecayed/filterNotDecayed; added isManeuverable tests
#              Henry Flushman
#
# This script is used to test the functionality of the SpaceObject class,
# SpaceTrackJSONParser, and the newly added SpaceObjectList.
# Follows PolySpace unit test conventions (see UnitTest-Constellation.py and UnitTest-PropagatorsParallelizerHandler.py).
# -----------------------------------------------------------------------------------------------------------------------

import os
import sys
import json
from datetime import date

PolySpacePath = os.getcwd()
sys.path.insert(0, PolySpacePath)

# configPolySpace initialization is optional in test contexts — skip if missing.
try:
    from configPolySpace import configPolySpace
    try:
        configPolySpace(PolySpacePath, updateSES=False)
    except Exception:
        print("configPolySpace setup skipped (orekit/data missing in test environment).")
except Exception:
    print("configPolySpace import skipped (not available).")

from SpaceObject import (
    SpaceObject,
    Payload,
    Debris,
    RocketBody,
    Unknown,
    SpaceTrackJSONParser,
    SpaceObjectList,
)

print("\n----------------------- SpaceObject Unit Test -----------------------")


def satcat_record(
    norad="25544",
    intldes="1998-067A",
    name="ISS (ZARYA)",
    obj_type="PAY",
    country="US",
    launch="1998-11-20",
    decay=None,
    rcs="0",
    rcs_size="LARGE",
    apogee=None,
    perigee=None,
    incl=None,
):
    rec = {
        "NORAD_CAT_ID": norad,
        "INTLDES": intldes,
        "OBJECT_NAME": name,
        "OBJECT_TYPE": obj_type,
        "COUNTRY_CODE": country,
        "LAUNCH_DATE": launch,
        "RCS_SIZE": rcs_size,
        "RCS": rcs,
    }
    if decay is not None:
        rec["DECAY_DATE"] = decay
    if apogee is not None:
        rec["APOGEE"] = apogee
    if perigee is not None:
        rec["PERIGEE"] = perigee
    if incl is not None:
        rec["INCLINATION"] = incl
    return rec


def gp_record(norad="25544", name="ISS (ZARYA)", epoch="2026-01-16T00:00:00.000000"):
    return {
        "NORAD_CAT_ID": norad,
        "OBJECT_NAME": name,
        "EPOCH": epoch,
        "MEAN_MOTION": "15.5",
        "ECCENTRICITY": "0.0001",
        "INCLINATION": "51.6",
        "RA_OF_ASC_NODE": "10.0",
        "ARG_OF_PERICENTER": "300.0",
        "MEAN_ANOMALY": "20.0",
        "BSTAR": "0.00012345",
    }


def assert_true(condition, pass_msg, fail_msg):
    if condition:
        print(pass_msg)
    else:
        print(fail_msg)


print("\n##################################### Success Cases #####################################\n")

# Test 1 - Default construction (manual mode, minimal)
try:
    o = SpaceObject()
    assert_true(
        o.getObjectType() == "UNKNOWN",
        "Test 1: Success: Default type UNKNOWN set correctly.",
        f"Test 1: Failed: Default type not UNKNOWN (got {o.getObjectType()}).",
    )
except Exception as e:
    print("Test 1: Failed (default construction):", e)

# Test 2 - Manual configuration mode uses user fields only
try:
    o = SpaceObject(
        rawRecord=None,
        objectType="DEBRIS",
        name="MANUAL OBJECT",
        noradID="11111",
        objectID="2099-001A",
        origin="US",
        launchDate="2099-01-01",
    )
    assert_true(
        o.name == "MANUAL OBJECT"
        and o.noradID == "11111"
        and o.objectID == "2099-001A",
        "Test 2: Success: Manual configuration fields set correctly.",
        f"Test 2: Failed: Manual configuration fields incorrect (name={o.name}, norad={o.noradID}, objid={o.objectID}).",
    )
except Exception as e:
    print("Test 2: Failed (manual configuration):", e)

# Test 3 - SATCAT record -> Payload subclass
try:
    rec = satcat_record(obj_type="PAY")
    o = SpaceObject.fromSpaceTrack(rec)
    assert_true(
        isinstance(o, Payload) and o.getObjectType() == "PAYLOAD",
        "Test 3: Success: SATCAT PAY mapped to Payload correctly.",
        "Test 3: Failed: SATCAT PAY did not map to Payload.",
    )
except Exception as e:
    print("Test 3: Failed (SATCAT PAY mapping):", e)

# Test 4 - SATCAT record -> Debris subclass
try:
    rec = satcat_record(norad="12345", intldes="2000-001A", name="TEST DEB", obj_type="DEB")
    o = SpaceObject.fromSpaceTrack(rec)
    assert_true(
        isinstance(o, Debris) and o.getObjectType() == "DEBRIS",
        "Test 4: Success: SATCAT DEB mapped to Debris correctly.",
        "Test 4: Failed: SATCAT DEB did not map to Debris.",
    )
except Exception as e:
    print("Test 4: Failed (SATCAT DEB mapping):", e)

# Test 5 - RocketBody variants
try:
    rec = satcat_record(norad="54321", intldes="2010-010B", name="TEST RB", obj_type="R/B")
    o = SpaceObject.fromSpaceTrack(rec)
    assert_true(
        isinstance(o, RocketBody) and o.getObjectType() == "ROCKET BODY",
        "Test 5: Success: SATCAT R/B mapped to RocketBody correctly.",
        "Test 5: Failed: SATCAT R/B did not map to RocketBody.",
    )
except Exception as e:
    print("Test 5: Failed (SATCAT R/B mapping):", e)

# Test 5b - Additional RB variants
try:
    variants = ["R-B", "RB", "rocket-body", "ROCKET_BODY", "r b"]
    ok = True
    for v in variants:
        rec = satcat_record(norad="666", intldes="2001-001A", name="TEST RB", obj_type=v)
        o = SpaceObject.fromSpaceTrack(rec)
        if not (isinstance(o, RocketBody) and o.getObjectType() == "ROCKET BODY"):
            ok = False
            break
    assert_true(
        ok,
        "Test 5b: Success: RocketBody variants normalized correctly.",
        "Test 5b: Failed: RocketBody variants did not normalize as expected.",
    )
except Exception as e:
    print("Test 5b: Failed (RocketBody variants):", e)

# Test 6 - GP-like record should be Unknown by type
try:
    rec = gp_record()
    o = SpaceObject.fromSpaceTrack(rec)
    assert_true(
        isinstance(o, Unknown) and o.getObjectType() == "UNKNOWN" and o.noradID == "25544",
        "Test 6: Success: GP-like record handled; UNKNOWN type and NORAD extracted.",
        f"Test 6: Failed: GP-like record not handled (type={o.getObjectType()}, norad={o.noradID}).",
    )
except Exception as e:
    print("Test 6: Failed (GP-like record):", e)

# Test 7 - JSON parser accepts list -> list of SpaceObjects
try:
    payload = [satcat_record(obj_type="PAY"), satcat_record(norad="2", intldes="1957-001B", name="SPUTNIK 1", obj_type="PAY")]
    objs = SpaceTrackJSONParser.parse(payload)
    assert_true(
        isinstance(objs, list) and len(objs) == 2 and isinstance(objs[0], SpaceObject),
        "Test 7: Parser Success: list payload converted into SpaceObjects.",
        "Test 7: Parser Failed: list payload did not convert as expected.",
    )
except Exception as e:
    print("Test 7: Parser Failed (list payload):", e)

# Test 8 - JSON parser accepts JSON string
try:
    payload_str = json.dumps([satcat_record(obj_type="PAY")])
    objs = SpaceTrackJSONParser.parse(payload_str)
    assert_true(len(objs) == 1 and objs[0].noradID == "25544", "Test 8: Parser Success: JSON string parsed into SpaceObjects.", "Test 8: Parser Failed: JSON string did not parse into SpaceObjects.")
except Exception as e:
    print("Test 8: Parser Failed (JSON string):", e)

# Test 9 - JSON parser accepts bytes
try:
    payload_bytes = json.dumps([satcat_record(obj_type="PAY")]).encode("utf-8")
    objs = SpaceTrackJSONParser.parse(payload_bytes)
    assert_true(len(objs) == 1 and objs[0].noradID == "25544", "Test 9: Parser Success: JSON bytes parsed into SpaceObjects.", "Test 9: Parser Failed: JSON bytes did not parse into SpaceObjects.")
except Exception as e:
    print("Test 9: Parser Failed (JSON bytes):", e)

# Test 10 - Full manual inputs with TLE
try:
    o = SpaceObject(
        rawRecord=None,
        objectType="PAYLOAD",
        name="ALL INPUTS",
        noradID="99999",
        objectID="2000-001A",
        origin="US",
        launchDate="2000-01-01",
        epoch="2026-01-01T00:00:00",
        tle_line1="1 99999U 20001A   26016.00000000  .00000000  00000-0  00000-0 0  9990",
        tle_line2="2 99999  98.0000  10.0000 0001000  20.0000 340.0000 14.00000000    01",
    )
    assert_true(
        o.hasTLE() and o.getObjectType() == "PAYLOAD",
        "Test 10: Success: All manual inputs handled; TLE detected.",
        "Test 10: Failed: All manual inputs not handled correctly.",
    )
except Exception as e:
    print("Test 10: Failed (all manual inputs):", e)

# Test 11 - getField / listFields
try:
    rec = satcat_record()
    o = SpaceObject.fromSpaceTrack(rec)
    assert_true(
        o.getField("OBJECT_NAME") == "ISS (ZARYA)" and "OBJECT_NAME" in o.listFields(),
        "Test 11: Success: getField and listFields behave correctly.",
        "Test 11: Failed: getField/listFields incorrect.",
    )
except Exception as e:
    print("Test 11: Failed (getField/listFields):", e)

# Test 12 - getRCSValue and getRCSSize parsing
try:
    rec = satcat_record(rcs="1.234", rcs_size="SMALL")
    o = SpaceObject.fromSpaceTrack(rec)
    assert_true(
        abs(o.getRCSValue() - 1.234) < 1e-9 and o.getRCSSize() == "SMALL",
        f"Test 12: Success: RCS value and size parsed correctly.",
        f"Test 12: Failed: RCS parsing incorrect (value={o.getRCSValue()}, size={o.getRCSSize()}).",
    )
except Exception as e:
    print("Test 12: Failed (RCS parsing):", e)

# Test 13 - isCurrent parsing variants
try:
    rec = satcat_record()
    rec["CURRENT"] = "Y"
    o = SpaceObject.fromSpaceTrack(rec)
    a = o.isCurrent()
    rec["CURRENT"] = "no"
    b = SpaceObject.fromSpaceTrack(rec).isCurrent()
    rec["CURRENT"] = "maybe"
    c = SpaceObject.fromSpaceTrack(rec).isCurrent()
    assert_true(
        a is True and b is False and c is None,
        "Test 13: Success: isCurrent handles multiple variants.",
        f"Test 13: Failed: isCurrent results unexpected (Y->{a}, no->{b}, maybe->{c}).",
    )
except Exception as e:
    print("Test 13: Failed (isCurrent):", e)

# Test 14 - parseByType filter
try:
    payload = [satcat_record(obj_type="PAY"), satcat_record(obj_type="DEB")]
    objs = SpaceTrackJSONParser.parse(payload)
    pays = SpaceTrackJSONParser.parseByType(payload, "PAYLOAD")
    assert_true(len(objs) == 2 and len(pays) == 1 and pays[0].getObjectType() == "PAYLOAD", "Test 14: Success: parseByType filters correctly.", "Test 14: Failed: parseByType did not filter correctly.")
except Exception as e:
    print("Test 14: Failed (parseByType):", e)

# Test 15 - getLaunchDate parsing (manual vs raw)
try:
    rec = satcat_record(launch="2001-02-03")
    o = SpaceObject.fromSpaceTrack(rec)
    ld1 = o.getLaunchDate()
    o2 = SpaceObject(rawRecord=None, launchDate="2010-05-06")
    ld2 = o2.getLaunchDate()
    assert_true(
        isinstance(ld1, date) and ld1.year == 2001 and isinstance(ld2, date) and ld2.year == 2010,
        f"Test 15: Success: Launch date parsed correctly from raw and manual inputs.",
        f"Test 15: Failed: launchDate parse issues (raw->{ld1}, manual->{ld2}).",
    )
except Exception as e:
    print("Test 15: Failed (launchDate parsing):", e)

# Test 16 - getEpochDate parsing with ISO format
try:
    rec = {"EPOCH": "2026-01-16T12:34:56.000000Z"}
    o = SpaceObject.fromSpaceTrack(rec)
    ed = o.getEpochDate()
    assert_true(isinstance(ed, date) and ed.year == 2026, "Test 16: Success: Epoch date parsed from ISO timestamp.", f"Test 16: Failed: epoch parse incorrect (got {ed}).")
except Exception as e:
    print("Test 16: Failed (epoch parsing):", e)

# Test 17 - filterByType ignores non-SpaceObject items and type-mismatch
try:
    objs = [SpaceObject.fromSpaceTrack(satcat_record(obj_type="PAY")), "not an object", 123]
    filtered = SpaceObject.filterByType(objs, "PAYLOAD")
    assert_true(len(filtered) == 1 and filtered[0].getObjectType() == "PAYLOAD", "Test 17: Success: filterByType ignores non SpaceObject entries.", "Test 17: Failed: filterByType did not behave as expected.")
except Exception as e:
    print("Test 17: Failed (filterByType):", e)

# Test 18 - isDecayed and filterDecayed / filterNotDecayed
try:
    rec_decayed = satcat_record(norad="51", decay="2020-01-15")
    rec_not_decayed = satcat_record(norad="52")
    o_decayed = SpaceObject.fromSpaceTrack(rec_decayed)
    o_not_decayed = SpaceObject.fromSpaceTrack(rec_not_decayed)
    assert_true(
        o_decayed.isDecayed() is True and o_not_decayed.isDecayed() is False,
        "Test 18: Success: isDecayed returns True for decayed objects, False for others.",
        f"Test 18: Failed: isDecayed incorrect (decayed={o_decayed.isDecayed()}, not_decayed={o_not_decayed.isDecayed()}).",
    )
except Exception as e:
    print("Test 18: Failed (isDecayed):", e)

# Test 19 - filterDecayed and filterNotDecayed static methods
try:
    objs = [
        SpaceObject.fromSpaceTrack(satcat_record(norad="61", decay="2010-01-01")),
        SpaceObject.fromSpaceTrack(satcat_record(norad="62")),
        SpaceObject.fromSpaceTrack(satcat_record(norad="63", decay="2015-06-15")),
        SpaceObject.fromSpaceTrack(satcat_record(norad="64")),
    ]
    decayed = SpaceObject.filterDecayed(objs)
    not_decayed = SpaceObject.filterNotDecayed(objs)
    assert_true(
        len(decayed) == 2 and len(not_decayed) == 2 and all(o.isDecayed() for o in decayed) and all(not o.isDecayed() for o in not_decayed),
        "Test 19: Success: filterDecayed and filterNotDecayed work correctly.",
        f"Test 19: Failed: decay filtering incorrect (decayed={len(decayed)}, not_decayed={len(not_decayed)}).",
    )
except Exception as e:
    print("Test 19: Failed (filterDecayed/filterNotDecayed):", e)

# Test 20 - isManeuverable returns True only for Payloads
try:
    payload = SpaceObject.fromSpaceTrack(satcat_record(obj_type="PAY"))
    debris = SpaceObject.fromSpaceTrack(satcat_record(obj_type="DEB"))
    rocket = SpaceObject.fromSpaceTrack(satcat_record(obj_type="R/B"))
    unknown = SpaceObject.fromSpaceTrack(satcat_record(obj_type="UNK"))
    
    assert_true(
        payload.isManeuverable() is True and 
        debris.isManeuverable() is False and 
        rocket.isManeuverable() is False and 
        unknown.isManeuverable() is False,
        "Test 20: Success: isManeuverable returns True only for Payloads.",
        f"Test 20: Failed: isManeuverable results incorrect (PAY={payload.isManeuverable()}, DEB={debris.isManeuverable()}, RB={rocket.isManeuverable()}, UNK={unknown.isManeuverable()}).",
    )
except Exception as e:
    print("Test 20: Failed (isManeuverable):", e)

print("\n##################################### New SpaceObjectList & Edge Case Tests #####################################\n")

# Test 21 - SpaceObjectList.from_list, __len__, __iter__, __getitem__, to_list
try:
    objs = [SpaceObject.fromSpaceTrack(satcat_record(obj_type="PAY")), SpaceObject.fromSpaceTrack(satcat_record(norad="2", obj_type="DEB"))]
    sol = SpaceObjectList.from_list(objs)
    assert_true(len(sol) == 2 and isinstance(iter(sol), type(iter(objs))) and sol[0] is objs[0] and isinstance(sol.to_list(), list), "Test 21: Success: SpaceObjectList basic behaviors (len/iter/getitem/to_list).", "Test 21: Failed: SpaceObjectList basic behaviors incorrect.")
except Exception as e:
    print("Test 21: Failed (SpaceObjectList basic behaviors):", e)

# Test 22 - SpaceObjectList.from_payload accepts list/dict/str/bytes via parser
try:
    payload = [satcat_record(obj_type="PAY")]
    sol1 = SpaceObjectList.from_payload(payload)
    sol2 = SpaceObjectList.from_payload(json.dumps(payload))
    sol3 = SpaceObjectList.from_payload(json.dumps(payload).encode("utf-8"))
    assert_true(len(sol1) == 1 and len(sol2) == 1 and len(sol3) == 1, "Test 22: Success: SpaceObjectList.from_payload accepts list/str/bytes.", "Test 22: Failed: from_payload variants did not produce expected results.")
except Exception as e:
    print("Test 22: Failed (from_payload):", e)

# Test 23 - append/extend and type checking
try:
    sol = SpaceObjectList()
    a = SpaceObject.fromSpaceTrack(satcat_record(obj_type="PAY"))
    sol.append(a)
    sol.extend([SpaceObject.fromSpaceTrack(satcat_record(norad="3", obj_type="DEB"))])
    assert_true(len(sol) == 2 and sol[0] is a and isinstance(sol[1], SpaceObject), "Test 23: Success: append and extend behave correctly.", "Test 23: Failed: append/extend incorrect.")
    # append wrong type should raise
    try:
        sol.append("not an object")
        print("Test 23b: Failed: append accepted non-SpaceObject.")
    except TypeError:
        print("Test 23b: Success: append rejected non-SpaceObject as expected.")
except Exception as e:
    print("Test 23: Failed (append/extend):", e)

# Test 24 - filter_by_type and convenience only_* wrappers and chaining
try:
    payload = [
        satcat_record(obj_type="PAY"),
        satcat_record(norad="9", obj_type="DEB"),
        satcat_record(norad="8", obj_type="R/B"),
    ]
    sol = SpaceObjectList.from_payload(payload)
    rockets = sol.only_rocket_bodies()
    debs = sol.only_debris()
    pays = sol.only_payloads()
    assert_true(len(rockets) == 1 and len(debs) == 1 and len(pays) == 1, "Test 24: Success: filter_by_type and only_* wrappers work.", "Test 24: Failed: type filters returned unexpected counts.")
    # chaining
    not_decayed_rockets = rockets.filter_not_decayed()  # should succeed without error
    assert_true(isinstance(not_decayed_rockets, SpaceObjectList), "Test 24b: Success: chaining filters returns SpaceObjectList.", "Test 24b: Failed: chaining didn't return SpaceObjectList.")
except Exception as e:
    print("Test 24: Failed (filter_by_type / only_*):", e)

# Test 25 - filter_decayed and filter_not_decayed in SpaceObjectList
try:
    recs = [
        satcat_record(norad="71", decay="2005-01-01"),
        satcat_record(norad="72"),
        satcat_record(norad="73", decay="2018-06-20"),
        satcat_record(norad="74"),
    ]
    sol = SpaceObjectList.from_payload(recs)
    decayed = sol.filter_decayed()
    not_decayed = sol.filter_not_decayed()
    assert_true(
        len(decayed) == 2 and len(not_decayed) == 2 and 
        all(o.isDecayed() for o in decayed) and 
        all(not o.isDecayed() for o in not_decayed),
        "Test 25: Success: filter_decayed and filter_not_decayed work in SpaceObjectList.",
        f"Test 25: Failed: decay filters incorrect (decayed={len(decayed)}, not_decayed={len(not_decayed)}).",
    )
except Exception as e:
    print("Test 25: Failed (filter_decayed/filter_not_decayed):", e)

# Test 26 - group_by_type, sort_by, and map
try:
    recs = [
        satcat_record(norad="31", obj_type="PAY", apogee="800"),
        satcat_record(norad="32", obj_type="DEB", apogee="1000"),
        satcat_record(norad="33", obj_type="R/B"),  # missing apogee
    ]
    sol = SpaceObjectList.from_payload(recs)
    grouped = sol.group_by_type()
    # group keys should include the normalized types
    has_pay = "PAYLOAD" in grouped
    has_deb = "DEBRIS" in grouped
    has_rb = "ROCKET BODY" in grouped
    # sort_by apogee should put missing apogee last
    sorted_sol = sol.sort_by("APOGEE")  # use raw field key resolution
    # map to names
    names = sol.map(lambda o: o.name)
    assert_true(has_pay and has_deb and has_rb and isinstance(sorted_sol, SpaceObjectList) and len(names) == 3, "Test 26: Success: group_by_type, sort_by, and map work.", "Test 26: Failed: group/sort/map behaviors unexpected.")
except Exception as e:
    print("Test 26: Failed (group/sort/map):", e)

# Test 27 - sort_by ensures missing values sort to end
try:
    rec_with = satcat_record(norad="41", apogee="1200")
    rec_without = satcat_record(norad="42")
    sol = SpaceObjectList.from_payload([rec_with, rec_without])
    sorted_sol = sol.sort_by("APOGEE")
    # first should be the one with apogee
    assert_true(sorted_sol[0].noradID == "41" and sorted_sol[1].noradID == "42", "Test 27: Success: sort_by places missing values last.", f"Test 27: Failed: sort_by result order {[o.noradID for o in sorted_sol]}")
except Exception as e:
    print("Test 27: Failed (sort_by missing values):", e)

# Test 28 - SpaceObjectList initialization with non-SpaceObject items should raise
try:
    try:
        SpaceObjectList(objects=["bad", 123])
        print("Test 28: Failed: SpaceObjectList accepted non-SpaceObject items at init.")
    except TypeError:
        print("Test 28: Success: SpaceObjectList rejected non-SpaceObject items at init as expected.")
except Exception as e:
    print("Test 28: Failed (SpaceObjectList init type checking):", e)

# Test 29 - filter_by_type with non-string obj_type should raise TypeError
try:
    sol = SpaceObjectList.from_payload([satcat_record(obj_type="PAY")])
    try:
        sol.filter_by_type(123)
        print("Test 29: Failed: filter_by_type accepted non-string obj_type.")
    except TypeError:
        print("Test 29: Success: filter_by_type rejected non-string obj_type as expected.")
except Exception as e:
    print("Test 29: Failed (filter_by_type type checking):", e)

# Test 30 - objectType setter accepts enum and string and normalizes
try:
    o = SpaceObject(rawRecord=None)
    o.objectType = "PAY"
    ok1 = o.getObjectType() == "PAYLOAD"
    o.objectType = o._normalize_object_type("DEB")  # supply an ObjectType (internal)
    ok2 = o.getObjectType() == "DEBRIS"
    assert_true(ok1 and ok2, "Test 30: Success: objectType setter accepts both string and enum-like values.", "Test 30: Failed: objectType setter did not accept both types.")
except Exception as e:
    print("Test 30: Failed (objectType setter):", e)

# Test 31 - launchDate/epoch setters accept date objects
try:
    o = SpaceObject(rawRecord=None)
    d = date(2020, 1, 2)
    o.launchDate = d
    o.epoch = d
    assert_true(isinstance(o.launchDate, date) and isinstance(o.epoch, date), "Test 31: Success: launchDate/epoch setters accept date objects.", f"Test 31: Failed: launchDate/epoch setters did not store date objects properly (launchDate={o.launchDate}, epoch={o.epoch}).")
except Exception as e:
    print("Test 31: Failed (date setters):", e)

print("\n##################################### Failure Cases #####################################\n")

# Test 32 - rawRecord wrong type -> TypeError
try:
    o = SpaceObject(rawRecord="not a dict")
    print("Test 32: Failed: No exception for rawRecord wrong type.")
except TypeError:
    print("Test 32: Success: Caught expected TypeError for rawRecord wrong type.")
except Exception as e:
    print("Test 32: Failed: Unexpected exception for rawRecord wrong type:", e)

# Test 33 - name wrong type -> TypeError
try:
    o = SpaceObject(rawRecord=None, name=123)
    print("Test 33: Failed: No exception for name wrong type.")
except TypeError:
    print("Test 33: Success: Caught expected TypeError for name wrong type.")
except Exception as e:
    print("Test 33: Failed: Unexpected exception for name wrong type:", e)

# Test 34 - noradID wrong type -> TypeError
try:
    o = SpaceObject(rawRecord=None, noradID=25544)
    print("Test 34: Failed: No exception for noradID wrong type.")
except TypeError:
    print("Test 34: Success: Caught expected TypeError for noradID wrong type.")
except Exception as e:
    print("Test 34: Failed: Unexpected exception for noradID wrong type:", e)

# Test 35 - Parser invalid JSON -> ValueError
try:
    objs = SpaceTrackJSONParser.parse("{ this is not valid json ]")
    print("Test 35: Failed: No exception for invalid JSON string.")
except ValueError:
    print("Test 35: Success: Caught expected ValueError for invalid JSON string.")
except Exception as e:
    print("Test 35: Failed: Unexpected exception for invalid JSON string:", e)

# Test 36 - Parser unsupported type -> TypeError
try:
    objs = SpaceTrackJSONParser.parse(12345)
    print("Test 36: Failed: No exception for unsupported payload type.")
except TypeError:
    print("Test 36: Success: Caught expected TypeError for unsupported payload type.")
except Exception as e:
    print("Test 36: Failed: Unexpected exception for unsupported payload type:", e)

# Test 37 - fromSpaceTrackBatch wrong type
try:
    SpaceObject.fromSpaceTrackBatch("not a list")
    print("Test 37: Failed: No exception for fromSpaceTrackBatch wrong type.")
except TypeError:
    print("Test 37: Success: Caught expected TypeError for fromSpaceTrackBatch wrong type.")
except Exception as e:
    print("Test 37: Failed: Unexpected exception for fromSpaceTrackBatch wrong type:", e)

# Test 38 - fromSpaceTrack records not dict in batch
try:
    SpaceObject.fromSpaceTrackBatch([{"OBJECT_TYPE": "PAY"}, "bad"])
    print("Test 38: Failed: No exception for non-dict in fromSpaceTrackBatch.")
except TypeError:
    print("Test 38: Success: Caught expected TypeError for non-dict record in batch.")
except Exception as e:
    print("Test 38: Failed: Unexpected exception for non-dict in fromSpaceTrackBatch:", e)

print("\n------------------- SpaceObject Unit Tests Complete -------------------\n")