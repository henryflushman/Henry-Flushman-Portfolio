# -----------------------------------
# Development History
# -------------------
# Jan 08 2026 - Created
# Modified  : 2026-02-02 - Added fixes, docstrings, private attribute refactor, and ObjectType enum
#           : 2026-02-04 - Added SpaceObjectList, cleaned small issues, improved typing
#           : 2026-02-17 - Replaced filterActive with filterDecayed/filterNotDecayed; added isManeuverable
#              Henry Flushman
#
# Description
# ----------
# This class defines Space Objects with subclasses for payloads,
# debris, rocket bodies, and unknown objects.
#
# Notes:
# - SpaceTrack data is provided as a dict (JSON -> dict)
# - Stores the full record so ALL fields are kept
# - Extract common fields into attributes for convenience
# - Handles multiple object constructions at once
# - Supports manual configuration
# -----------------------------------

"""
SpaceObject module

Provides:
- SpaceObject: smart wrapper around Space-Track / SATCAT-like records.
- Payload, Debris, RocketBody, Unknown: small typed subclasses.
- SpaceTrackJSONParser: helper to parse JSON payloads into SpaceObject instances.
- SpaceObjectList: container for collections of SpaceObjects with filtering utilities.

Design changes:
- Internal storage uses private attributes (e.g., _name, _objectID) to avoid property recursion.
- Public attributes are exposed via properties with getters and setters for backward compatibility.
- ObjectType Enum introduced for stronger internal handling; public methods return normalized strings.
"""

import json
from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable

# Type alias for clarity
Number = Union[int, float]


class ObjectType(Enum):
    """Enum representing normalized object types used internally."""
    PAYLOAD = "PAYLOAD"
    DEBRIS = "DEBRIS"
    ROCKET_BODY = "ROCKET BODY"
    UNKNOWN = "UNKNOWN"


class SpaceObject:
    """
    Represents a single Space-Track object record (SATCAT-like).

    Internal storage uses private attributes to avoid property recursion and to make
    behavior deterministic. Public properties remain available and assignable.
    """

    def __init__(
        self,
        rawRecord: Optional[Dict[str, Any]] = None,
        objectType: Optional[str] = None,
        name: Optional[str] = None,
        noradID: Optional[str] = None,
        objectID: Optional[str] = None,
        origin: Optional[str] = None,
        launchDate: Optional[str] = None,
        epoch: Optional[str] = None,
        tle_line1: Optional[str] = None,
        tle_line2: Optional[str] = None,
    ):
        """
        Initialize a SpaceObject.

        Two modes:
        - rawRecord mode: pass in a dict (Space-Track record) and fields are extracted.
        - manual mode: pass rawRecord=None and supply fields via kwargs.

        All string-like inputs are validated to be str or None.
        """
        # Mode selection
        self._raw_mode = rawRecord is not None

        if rawRecord is None:
            rawRecord = {}
        if not isinstance(rawRecord, dict):
            raise TypeError(f"rawRecord must be a dict. Got {type(rawRecord).__name__}")

        for arg_name, arg_val in [
            ("objectType", objectType),
            ("name", name),
            ("noradID", noradID),
            ("objectID", objectID),
            ("origin", origin),
            ("launchDate", launchDate),
            ("epoch", epoch),
            ("tle_line1", tle_line1),
            ("tle_line2", tle_line2),
        ]:
            if arg_val is not None and not isinstance(arg_val, str) and not isinstance(arg_val, date):
                # allow date objects for date fields
                if arg_name in ("launchDate", "epoch") and isinstance(arg_val, date):
                    continue
                raise TypeError(f"{arg_name} must be a string, date, or None. Got {type(arg_val).__name__}")

        # preserve raw incoming record
        self.rawRecord: Dict[str, Any] = rawRecord

        # Private storage (do not expose directly to avoid recursion)
        self._noradID: Optional[str] = None
        self._objectID: Optional[str] = None
        self._name: Optional[str] = None
        self._origin: Optional[str] = None
        self._launchDate: Optional[Union[str, date]] = None
        self._epoch: Optional[Union[str, date]] = None
        self._tle_line1: Optional[str] = None
        self._tle_line2: Optional[str] = None
        self._rcs: Any = None
        self._rcs_size: Any = None
        # store object type internally as enum
        self._objectType: ObjectType = ObjectType.UNKNOWN

        # Manual configuration: set private attributes and done
        if not self._raw_mode:
            self._noradID = noradID
            self._objectID = objectID
            self._name = name
            self._origin = origin
            self._launchDate = launchDate
            self._epoch = epoch
            self._tle_line1 = tle_line1
            self._tle_line2 = tle_line2
            resolved = objectType if objectType is not None else "UNKNOWN"
            self._objectType = self._normalize_object_type(resolved)
            return

        # rawData mode: extract from rawRecord (constructor overrides preferred)
        if noradID is not None:
            self._noradID = noradID
        else:
            raw_norad = self.rawRecord.get("NORAD_CAT_ID")
            if raw_norad is not None and str(raw_norad).strip() != "":
                self._noradID = str(raw_norad).strip()
            else:
                self._noradID = self._coalesce_str(
                    self.rawRecord.get("NORAD_ID"),
                    self.rawRecord.get("CATALOG_NUMBER"),
                )

        if objectID is not None:
            self._objectID = objectID
        else:
            raw_objid = (
                self.rawRecord.get("OBJECT_ID")
                or self.rawRecord.get("INTLDES")
                or self.rawRecord.get("INTERNATIONAL_DESIGNATOR")
            )
            if raw_objid is not None and str(raw_objid).strip() != "":
                self._objectID = str(raw_objid).strip()
            else:
                self._objectID = None

        self._name = name if name is not None else self._coalesce_str(
            self.rawRecord.get("OBJECT_NAME"),
            self.rawRecord.get("SATNAME"),
            self.rawRecord.get("NAME"),
        )

        self._origin = origin if origin is not None else self._coalesce_str(
            self.rawRecord.get("COUNTRY_CODE"),
            self.rawRecord.get("OWNER"),
            self.rawRecord.get("COUNTRY"),
        )

        self._launchDate = launchDate if launchDate is not None else self._coalesce_str(
            self.rawRecord.get("LAUNCH_DATE"),
            self.rawRecord.get("LAUNCH"),
        )

        self._epoch = epoch if epoch is not None else self._coalesce_str(
            self.rawRecord.get("EPOCH"),
            self.rawRecord.get("EPOCH_DATE"),
        )

        self._tle_line1 = tle_line1 if tle_line1 is not None else self._coalesce_str(
            self.rawRecord.get("TLE_LINE1"),
            self.rawRecord.get("LINE1"),
        )
        self._tle_line2 = tle_line2 if tle_line2 is not None else self._coalesce_str(
            self.rawRecord.get("TLE_LINE2"),
            self.rawRecord.get("LINE2"),
        )

        self._rcs = self.rawRecord.get("RCS")
        self._rcs_size = self.rawRecord.get("RCS_SIZE")

        resolved = objectType if objectType is not None else (self.rawRecord.get("OBJECT_TYPE") or "UNKNOWN")
        if resolved is not None and not isinstance(resolved, (str, ObjectType)):
            raise ValueError(f"objectType must resolve to a string or ObjectType. Got {type(resolved).__name__}")
        self._objectType = self._normalize_object_type(resolved)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}: "
            f"{{Name: {self.name}, ID: {self.objectID}, NORAD: {self.noradID}, Type: {self.getObjectType()}}}"
        )

    # ------------------------
    # Helper / normalization functions
    # ------------------------

    @staticmethod
    def _coalesce_str(*vals) -> Optional[str]:
        """Return the first non-empty value from vals converted to a stripped str, or None."""
        for v in vals:
            if v is None:
                continue
            s = str(v).strip()
            if s != "":
                return s
        return None

    @staticmethod
    def _normalize_object_type(obj_type) -> ObjectType:
        """
        Normalize many variant strings for object type into an ObjectType enum member.
        Accepts strings or ObjectType; returns ObjectType.
        """
        if isinstance(obj_type, ObjectType):
            return obj_type
        if obj_type is None:
            return ObjectType.UNKNOWN

        t = str(obj_type).strip().upper()
        t = t.replace("/", " ").replace("\\", " ").replace("-", " ").replace("_", " ")
        t = " ".join(t.split())

        if t == "" or t.isdigit():
            return ObjectType.UNKNOWN
        if t in ("PAY", "PAYLOAD"):
            return ObjectType.PAYLOAD
        if t in ("DEB", "DEBRIS"):
            return ObjectType.DEBRIS
        if t in ("RB", "R B") or "ROCKET" in t:
            return ObjectType.ROCKET_BODY
        if t in ("UNK", "UNKNOWN"):
            return ObjectType.UNKNOWN
        return ObjectType.UNKNOWN

    # ------------------------
    # Main API functions
    # ------------------------

    def getField(self, fieldName: str, default=None):
        """
        Return a raw field value from the stored rawRecord.

        Args:
            fieldName (str): field key to fetch
            default: returned if the key is not present
        """
        if not isinstance(fieldName, str):
            raise TypeError(f"fieldName must be a string. Got {type(fieldName).__name__}")
        return self.rawRecord.get(fieldName, default)

    def listFields(self) -> List[str]:
        """Return a list of all keys present in rawRecord."""
        return list(self.rawRecord.keys())

    def get_str(self, *field_names: str, default: Optional[str] = None) -> Optional[str]:
        """Return the first non-empty rawRecord field (converted to str) among field_names, else default."""
        # Use coalesce, but preserve explicit default even if it's falsy (None is usual)
        val = self._coalesce_str(*(self.rawRecord.get(f) for f in field_names))
        return val if val is not None else default

    def get_float(self, *field_names: str, default: Optional[float] = None) -> Optional[float]:
        """Return the first field from rawRecord that can be parsed as float, else default."""
        for f in field_names:
            v = self.rawRecord.get(f)
            if v is None:
                continue
            try:
                s = str(v).strip()
                if s == "":
                    continue
                return float(s)
            except (ValueError, TypeError):
                continue
        return default

    def get_int(self, *field_names: str, default: Optional[int] = None) -> Optional[int]:
        """Return the first field from rawRecord that can be parsed as int, else default."""
        for f in field_names:
            v = self.rawRecord.get(f)
            if v is None:
                continue
            try:
                s = str(v).strip()
                if s == "":
                    continue
                return int(float(s))
            except (ValueError, TypeError):
                continue
        return default

    def get_date(self, *field_names: str, default: Optional[date] = None) -> Optional[date]:
        """
        Try to parse the first available field from rawRecord into a datetime.date.
        Supports several common formats and ISO with optional 'Z'.
        """
        for f in field_names:
            v = self.rawRecord.get(f)
            if v is None:
                continue
            s = str(v).strip()
            if s == "":
                continue
            # try several formats (slice to allow some trailing characters)
            for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(s[:19], fmt).date()
                except Exception:
                    pass
            try:
                return datetime.fromisoformat(s.replace("Z", "")).date()
            except Exception:
                continue
        return default

    # ATTRIBUTE GETTERS / PROPERTIES

    def getObjectType(self) -> str:
        """Return the normalized object type string (PAYLOAD/DEBRIS/ROCKET BODY/UNKNOWN)."""
        return self._objectType.value

    def hasTLE(self) -> bool:
        """Return True if both TLE lines are present (non-empty)."""
        return bool(self._tle_line1 and self._tle_line2)

    def getTLE(self) -> Optional[str]:
        """Return TLE lines joined by newline, or None if absent."""
        if not self.hasTLE():
            return None
        return f"{self._tle_line1}\n{self._tle_line2}"

    def getNORAD(self) -> Optional[str]:
        """Return NORAD catalog identifier string if available."""
        return self._noradID

    def getObjectID(self) -> Optional[str]:
        """Return international designator / object ID (prefers stored private attribute)."""
        if self._objectID is not None:
            return self._objectID
        return self._coalesce_str(
            self.rawRecord.get("OBJECT_ID"),
            self.rawRecord.get("INTLDES"),
            self.rawRecord.get("INTERNATIONAL_DESIGNATOR"),
        )

    def getName(self) -> Optional[str]:
        """Return the stored name (prefer initialized/private attribute)."""
        if self._name is not None:
            return self._name
        return self._coalesce_str(
            self.rawRecord.get("OBJECT_NAME"),
            self.rawRecord.get("SATNAME"),
            self.rawRecord.get("NAME"),
        )

    def getCountry(self) -> Optional[str]:
        """Return country/origin (cached in _origin or read from rawRecord variants)."""
        return self._origin or self.get_str("COUNTRY", "COUNTRY_CODE", "OWNER")

    def getLaunchDate(self) -> Optional[date]:
        """
        Return launch date as datetime.date.

        Prefers manual/private attribute (string/date) then falls back to rawRecord.
        """
        v = self._launchDate
        if v is not None:
            if isinstance(v, date):
                return v
            s = str(v).strip()
            if s != "":
                for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                    try:
                        return datetime.strptime(s[:19], fmt).date()
                    except Exception:
                        pass
                try:
                    return datetime.fromisoformat(s.replace("Z", "")).date()
                except Exception:
                    pass
        return self.get_date("LAUNCH_DATE", "LAUNCH")

    def getDecayDate(self) -> Optional[date]:
        """Return decay date as datetime.date parsed from rawRecord."""
        return self.get_date("DECAY_DATE", "DECAY")

    def getEpochDate(self) -> Optional[date]:
        """Return epoch date as datetime.date (prefers private attribute if present)."""
        v = self._epoch
        if v is not None:
            if isinstance(v, date):
                return v
            s = str(v).strip()
            if s != "":
                for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                    try:
                        return datetime.strptime(s[:19], fmt).date()
                    except Exception:
                        pass
                try:
                    return datetime.fromisoformat(s.replace("Z", "")).date()
                except Exception:
                    pass
        return self.get_date("EPOCH", "EPOCH_DATE")

    def getApogee(self) -> Optional[float]:
        """Return apogee float from rawRecord."""
        return self.get_float("APOGEE")

    def getPerigee(self) -> Optional[float]:
        """Return perigee float from rawRecord."""
        return self.get_float("PERIGEE")

    def getInclination(self) -> Optional[float]:
        """Return inclination float from rawRecord."""
        return self.get_float("INCLINATION", "INCL")

    def getPeriod(self) -> Optional[float]:
        """Return period float from rawRecord."""
        return self.get_float("PERIOD")

    def getRCSValue(self) -> Optional[float]:
        """Return RCS value parsed to float if present in rawRecord."""
        return self.get_float("RCS", "RCSVALUE")

    def getRCSSize(self) -> Optional[str]:
        """Return RCS size (prefer private attribute)."""
        if self._rcs_size is not None:
            return self._rcs_size
        return self.get_str("RCS_SIZE")

    def getIntlDes(self) -> Optional[str]:
        """Return international designator string from rawRecord variants."""
        return self.get_str("INTLDES", "OBJECT_ID", "INTERNATIONAL_DESIGNATOR")

    def getSite(self) -> Optional[str]:
        """Return site string from rawRecord if present."""
        return self.get_str("SITE")

    # Properties: expose public attribute names while storing in private attributes.
    @property
    def noradID(self) -> Optional[str]:
        return self._noradID

    @noradID.setter
    def noradID(self, val: Optional[str]):
        self._noradID = val

    @property
    def objectID(self) -> Optional[str]:
        return self.getObjectID()

    @objectID.setter
    def objectID(self, val: Optional[str]):
        self._objectID = val

    @property
    def name(self) -> Optional[str]:
        return self.getName()

    @name.setter
    def name(self, val: Optional[str]):
        self._name = val

    @property
    def origin(self) -> Optional[str]:
        return self._origin

    @origin.setter
    def origin(self, val: Optional[str]):
        self._origin = val

    @property
    def launchDate(self) -> Optional[date]:
        return self.getLaunchDate()

    @launchDate.setter
    def launchDate(self, val: Optional[Union[str, date]]):
        # allow setter to accept date or string
        if isinstance(val, date):
            self._launchDate = val
        else:
            self._launchDate = val

    @property
    def epoch(self) -> Optional[date]:
        return self.getEpochDate()

    @epoch.setter
    def epoch(self, val: Optional[Union[str, date]]):
        if isinstance(val, date):
            self._epoch = val
        else:
            self._epoch = val

    @property
    def tle_line1(self) -> Optional[str]:
        return self._tle_line1

    @tle_line1.setter
    def tle_line1(self, val: Optional[str]):
        self._tle_line1 = val

    @property
    def tle_line2(self) -> Optional[str]:
        return self._tle_line2

    @tle_line2.setter
    def tle_line2(self, val: Optional[str]):
        self._tle_line2 = val

    @property
    def rcs(self):
        return self._rcs

    @rcs.setter
    def rcs(self, val):
        self._rcs = val

    @property
    def rcs_size(self):
        return self.getRCSSize()

    @rcs_size.setter
    def rcs_size(self, val):
        self._rcs_size = val

    @property
    def objectType(self) -> str:
        """Public property returns normalized object type string."""
        return self._objectType.value

    @objectType.setter
    def objectType(self, val: Union[str, ObjectType]):
        """Allow setting objectType via string or ObjectType enum."""
        self._objectType = self._normalize_object_type(val)

    # Additional convenience properties (older API)
    @property
    def apogee(self):
        return self.getApogee()

    @property
    def perigee(self):
        return self.getPerigee()

    @property
    def inclination(self):
        return self.getInclination()

    @property
    def tle(self):
        return self.getTLE()

    @property
    def norad(self):
        return self.getNORAD()

    @property
    def period(self):
        return self.getPeriod()

    @property
    def country(self):
        return self.getCountry()

    @property
    def decayDate(self):
        return self.getDecayDate()

    @staticmethod
    def listProperties() -> List[str]:
        """
        Return a list of commonly used public properties for SpaceObject.
        Kept for backward compatibility with earlier APIs.
        """
        return [
            'noradID', 'objectID', 'name', 'origin', 'launchDate',
            'epoch', 'tle_line1', 'tle_line2', 'rcs', 'rcs_size',
            'objectType', 'apogee', 'perigee', 'inclination', 'tle',
            'norad', 'period', 'country', 'decayDate'
        ]

    # Logical helpers
    def isCurrent(self) -> Optional[bool]:
        """Parse CURRENT field to boolean (Y/YES/TRUE/1 -> True, N/NO/FALSE/0 -> False)."""
        v = self.getField("CURRENT")
        if v is None:
            return None
        s = str(v).strip().upper()
        if s in ("Y", "YES", "TRUE", "1"):
            return True
        if s in ("N", "NO", "FALSE", "0"):
            return False
        return None

    def isDecayed(self) -> bool:
        """
        Return True if the object has a decay date set (has decayed/re-entered).
        Return False if no decay date is available (still in orbit).
        """
        return self.getDecayDate() is not None

    def isManeuverable(self) -> bool:
        """
        Return True if object is a Payload AND has RCS (Radar Cross Section) value.
        Return False for all other types (Debris, RocketBody, Unknown are not maneuverable).
        
        Maneuverability requires:
        - Object type is PAYLOAD (only payloads have propulsion capability)
        - Object has a non-None RCS value (indicates it's trackable and likely active)
        
        Maneuverability is only applicable to active payloads with propulsion capability.
        """
        # First filter: must be a Payload
        if self.getObjectType() != "PAYLOAD":
            return False
    
        # Second filter: must have RCS value
        rcs_value = self.getRCSValue()
        return rcs_value is not None

    def getOrbitSummary(self) -> Dict[str, Optional[float]]:
        return {
            "apogee": self.getApogee(),
            "perigee": self.getPerigee(),
            "inclination": self.getInclination(),
            "period": self.getPeriod(),
        }

    @property
    def orbitSummary(self):
        return self.getOrbitSummary()

    # ------------------------
    # Class / factory Methods
    # ------------------------

    @classmethod
    def fromSpaceTrack(cls, rawRecord: Dict[str, Any]) -> "SpaceObject":
        """
        Create a typed SpaceObject subclass instance based on rawRecord['OBJECT_TYPE'].
        """
        if rawRecord is None or not isinstance(rawRecord, dict):
            raise TypeError(f"rawRecord must be a dict. Got {type(rawRecord).__name__}")

        objType = rawRecord.get("OBJECT_TYPE") or "UNKNOWN"
        objType_norm = cls._normalize_object_type(objType)

        if objType_norm == ObjectType.PAYLOAD:
            return Payload(rawRecord)
        elif objType_norm == ObjectType.DEBRIS:
            return Debris(rawRecord)
        elif objType_norm == ObjectType.ROCKET_BODY:
            return RocketBody(rawRecord)
        else:
            return Unknown(rawRecord)

    @classmethod
    def fromSpaceTrackBatch(cls, rawData: List[Dict[str, Any]]) -> List["SpaceObject"]:
        """
        Convert a list of dict records into a list of SpaceObject instances.
        """
        if rawData is None or not isinstance(rawData, list):
            raise TypeError(f"rawData must be a list of dict records. Got {type(rawData).__name__}")

        objects: List[SpaceObject] = []
        for record in rawData:
            if not isinstance(record, dict):
                raise TypeError(f"Each record must be a dict. Got {type(record).__name__}")
            objects.append(cls.fromSpaceTrack(record))
        return objects

    @staticmethod
    def filterByType(objects: List["SpaceObject"], obj_type: str) -> List["SpaceObject"]:
        """
        Filter a list of SpaceObjects to those matching normalized obj_type.
        """
        if not isinstance(obj_type, str):
            raise TypeError("obj_type must be a string")
        want = SpaceObject._normalize_object_type(obj_type)
        return [o for o in objects if isinstance(o, SpaceObject) and o._objectType == want]

    @staticmethod
    def filterDecayed(objects: List["SpaceObject"]) -> List["SpaceObject"]:
        """
        Filter a list of SpaceObjects to those that have decayed (have a decay date).

        Rules:
        - decayDate must be not None (object has re-entered)

        Returns:
            list of SpaceObject with decay dates
        """
        return [o for o in objects if isinstance(o, SpaceObject) and o.getDecayDate() is not None]

    @staticmethod
    def filterNotDecayed(objects: List["SpaceObject"]) -> List["SpaceObject"]:
        """
        Filter a list of SpaceObjects to those that have NOT decayed (no decay date).

        Rules:
        - decayDate must be None (object is still in orbit)

        Returns:
            list of SpaceObject without decay dates
        """
        return [o for o in objects if isinstance(o, SpaceObject) and o.getDecayDate() is None]

    @staticmethod
    def onlyPayloads(objects: List["SpaceObject"]) -> List["SpaceObject"]:
        return SpaceObject.filterByType(objects, "PAYLOAD")

    @staticmethod
    def onlyDebris(objects: List["SpaceObject"]) -> List["SpaceObject"]:
        return SpaceObject.filterByType(objects, "DEBRIS")

    @staticmethod
    def onlyRocketBodies(objects: List["SpaceObject"]) -> List["SpaceObject"]:
        return SpaceObject.filterByType(objects, "ROCKET BODY")

    @staticmethod
    def onlyUnknown(objects: List["SpaceObject"]) -> List["SpaceObject"]:
        return SpaceObject.filterByType(objects, "UNKNOWN")


class Payload(SpaceObject):
    """Payload-type SpaceObject (convenience subclass)."""

    def __init__(self, rawRecord: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(rawRecord=rawRecord, objectType="PAYLOAD", **kwargs)


class Debris(SpaceObject):
    """Debris-type SpaceObject (convenience subclass)."""

    def __init__(self, rawRecord: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(rawRecord=rawRecord, objectType="DEBRIS", **kwargs)


class RocketBody(SpaceObject):
    """Rocket body-type SpaceObject (convenience subclass)."""

    def __init__(self, rawRecord: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(rawRecord=rawRecord, objectType="ROCKET BODY", **kwargs)


class Unknown(SpaceObject):
    """Unknown-type SpaceObject (convenience subclass)."""

    def __init__(self, rawRecord: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(rawRecord=rawRecord, objectType="UNKNOWN", **kwargs)


class SpaceTrackJSONParser:
    """
    Helper to parse Space-Track JSON responses into SpaceObject instances.
    """

    @staticmethod
    def parse(payload):
        """
        Parse payload into one or more SpaceObject instances.

        Accepts bytes, str, dict, or list.
        """
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8", errors="replace")

        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception as e:
                raise ValueError("Invalid JSON payload received (json.loads failed).") from e

        if isinstance(payload, dict):
            return [SpaceObject.fromSpaceTrack(payload)]

        if isinstance(payload, list):
            return SpaceObject.fromSpaceTrackBatch(payload)

        raise TypeError(f"Unsupported payload type after parsing: {type(payload).__name__}")

    @staticmethod
    def parseByType(
        payload: Union[str, bytes, Dict[str, Any], List[Dict[str, Any]]],
        obj_type: str,
    ) -> List[SpaceObject]:
        """Parse payload then filter by normalized obj_type."""
        objects = SpaceTrackJSONParser.parse(payload)
        return SpaceObject.filterByType(objects, obj_type)


class SpaceObjectList:
    """
    Container for many SpaceObject instances with convenient filtering helpers.

    Usage examples:
      - sol = SpaceObjectList.from_payload(json_bytes_or_str)
      - rocket_bodies = sol.filter_by_type("ROCKET BODY")
      - decayed = sol.filter_decayed()
      - not_decayed = sol.filter_not_decayed()
      - filtered = sol.filter(name="ISS")                  # exact (case-insensitive) match on .name
      - filtered = sol.filter(name=lambda v: v and "ISS" in v)  # usable predicate
      - filtered = sol.filter(apogee=lambda v: v is not None and v > 500)
    """

    def __init__(self, objects: Optional[List[SpaceObject]] = None):
        self._objects: List[SpaceObject] = list(objects) if objects else []
        for o in self._objects:
            if not isinstance(o, SpaceObject):
                raise TypeError("SpaceObjectList expects SpaceObject instances")

    @classmethod
    def from_payload(cls, payload) -> "SpaceObjectList":
        """Parse JSON/bytes/str/dict/list payload via SpaceTrackJSONParser and return a SpaceObjectList."""
        objects = SpaceTrackJSONParser.parse(payload)
        return cls(objects)

    @classmethod
    def from_list(cls, objects: List[SpaceObject]) -> "SpaceObjectList":
        return cls(objects)

    def __len__(self) -> int:
        return len(self._objects)

    def __iter__(self):
        return iter(self._objects)

    def __getitem__(self, idx):
        return self._objects[idx]

    def __repr__(self):
        return f"SpaceObjectList(len={len(self)})"

    def to_list(self) -> List[SpaceObject]:
        """Return a shallow copy of the internal list."""
        return list(self._objects)

    def append(self, obj: SpaceObject):
        """Append a SpaceObject to the list."""
        if not isinstance(obj, SpaceObject):
            raise TypeError("append expects a SpaceObject")
        self._objects.append(obj)

    def extend(self, objs: List[SpaceObject]):
        for o in objs:
            self.append(o)

    # Specific filters
    def filter_by_type(self, obj_type: str) -> "SpaceObjectList":
        """Return SpaceObjectList of objects whose normalized type matches obj_type."""
        filtered = SpaceObject.filterByType(self._objects, obj_type)
        return SpaceObjectList(filtered)

    def filter_decayed(self) -> "SpaceObjectList":
        """
        Return SpaceObjectList of objects that have decayed (have decay dates).
        """
        filtered = SpaceObject.filterDecayed(self._objects)
        return SpaceObjectList(filtered)

    def filter_not_decayed(self) -> "SpaceObjectList":
        """
        Return SpaceObjectList of objects that have NOT decayed (no decay dates).
        """
        filtered = SpaceObject.filterNotDecayed(self._objects)
        return SpaceObjectList(filtered)
    
    def filter_maneuverable(self) -> "SpaceObjectList":
        """
        Return SpaceObjectList of objects that are maneuverable (Payloads with RCS value).
         - Object type must be PAYLOAD
         - RCS value must be not None
        """
        filtered = [o for o in self._objects if isinstance(o, SpaceObject) and o.isManeuverable()]
        return SpaceObjectList(filtered)

    # Convenience wrappers
    def only_payloads(self) -> "SpaceObjectList":
        return self.filter_by_type("PAYLOAD")

    def only_debris(self) -> "SpaceObjectList":
        return self.filter_by_type("DEBRIS")

    def only_rocket_bodies(self) -> "SpaceObjectList":
        return self.filter_by_type("ROCKET BODY")

    def only_unknown(self) -> "SpaceObjectList":
        return self.filter_by_type("UNKNOWN")

    # General-purpose filter
    def filter(self, **criteria) -> "SpaceObjectList":
        """
        Generic filter supporting:
         - exact matches (strings compared case-insensitively and stripped),
         - membership tests for collections,
         - None checks,
         - callables as predicates that accept the attribute value and return bool.

        Attribute resolution:
         - First tries getattr(obj, attr)
         - If not present, tries obj.getField(attr) (use raw field keys)
        """
        def resolve_attr(obj: SpaceObject, attr: str):
            # prefer public property/attribute
            if hasattr(obj, attr):
                try:
                    return getattr(obj, attr)
                except Exception:
                    return None
            # fallback: try rawRecord field name (case-sensitive then upper)
            val = obj.getField(attr)
            if val is None:
                val = obj.getField(attr.upper())
            return val

        out: List[SpaceObject] = []
        for o in self._objects:
            keep = True
            for attr, cond in criteria.items():
                val = resolve_attr(o, attr)
                # callable predicate
                if callable(cond):
                    try:
                        if not cond(val):
                            keep = False
                            break
                    except Exception:
                        keep = False
                        break
                else:
                    # membership
                    if isinstance(cond, (list, tuple, set)):
                        if val not in cond:
                            keep = False
                            break
                    elif cond is None:
                        if val is not None:
                            keep = False
                            break
                    # string-insensitive compare
                    elif isinstance(cond, str) and isinstance(val, str):
                        if val.strip().lower() != cond.strip().lower():
                            keep = False
                            break
                    else:
                        if val != cond:
                            keep = False
                            break
            if keep:
                out.append(o)
        return SpaceObjectList(out)

    # Utilities
    def group_by_type(self) -> Dict[str, "SpaceObjectList"]:
        """
        Group objects by normalized object type value and return a dict of type->SpaceObjectList.
        Types are strings matching ObjectType.value (PAYLOAD, DEBRIS, ROCKET BODY, UNKNOWN).
        """
        groups: Dict[str, List[SpaceObject]] = {}
        for o in self._objects:
            k = o.objectType if hasattr(o, "objectType") else o.getObjectType()
            groups.setdefault(k, []).append(o)
        return {k: SpaceObjectList(v) for k, v in groups.items()}

    def sort_by(self, attr: str, reverse: bool = False) -> "SpaceObjectList":
        """
        Return a new SpaceObjectList sorted by attribute attr.
        Attribute resolution uses getattr first, then rawRecord field.
        Missing values sort to the end.
        """
        def keyfn(o: SpaceObject):
            v = getattr(o, attr, None)
            if v is None:
                v = o.getField(attr) or o.getField(attr.upper())
            # ensure comparable; None -> sorts last
            return (v is None, v)
        sorted_list = sorted(self._objects, key=keyfn, reverse=reverse)
        return SpaceObjectList(sorted_list)

    def map(self, fn: Callable[[SpaceObject], Any]) -> List[Any]:
        """Apply fn to each SpaceObject and return a list of results."""
        return [fn(o) for o in self._objects]