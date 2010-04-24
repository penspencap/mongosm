import pymongo
from pymongo import Connection
from xml.sax.saxutils import escape

class OsmApi:
    def __init__(self):
        self.client = Connection()

    def getNodesInBounds(self, box):
        cursor = self.client.osm.nodes.find({'loc' : { '$within' : { '$box' : box } } })
        nodes = []

        for row in cursor:
            nodes.append(row)

        return nodes

    def getNodesFromWays(self, ways):
        nodeIds = set()

        for way in ways:
            for nodeId in way['nodes']:
                nodeIds.add(nodeId)

        nodes = []
        for nodeId in nodeIds:
            node = self.client.osm.nodes.find_one({'id' : nodeId})
            if node:
                nodes.append(node)
            else:
                print "Error. couldn't find node id %d." % nodeId

        return nodes
        

    def getWaysFromNodes(self, nodes):
        wayIds = set()

        for node in nodes:
            wayIdsFromNode = self.getWayIdsUsingNodeId(node['id'])

            for wayId in wayIdsFromNode:
                wayIds.add(wayId)

        ways = []

        for wayId in wayIds:
            way = self.client.osm.ways.find_one({'id' : wayId})
            if way:
                ways.append(way)
            else:
                print "Error. Couldn't find way id %d." % wayId

#        cursor = self.client.osm.ways.find().where("{'id' : { '$all' : [%s] } }" % (','.join([str(y) for y in wayIds])))
#        for row in cursor:
#            ways.append(row)

        return ways

    def getWayIdsUsingNodeId(self, id):
        cursor = self.client.osm.nodes.find_one({'id' : id })
        if cursor and 'ways' in cursor:
            return cursor['ways']
        else:
            return []
    
    def getRelationsFromWays(self, ways):
        relationIds = set()
        
        for way in ways:
            id = way['id']
            relationIdsFromWay = self.getRelationIdsUsingWayId(id)

            for relationId in relationIdsFromWay:
                relationIds.add(relationId)

        relations = []

        for relationId in relationIds:
            relation = self.client.osm.relations.find_one({'id' : relationId})
            if relation:
                relations.append(relation)
            else:
                print "Error. Couldn't find relation id %d." % relationId

        return relations

    def getRelationIdsUsingWayId(self, id):
        cursor = self.client.osm.ways.find_one({'id' : id })
        if cursor and 'relations' in cursor:
            return cursor['relations']
        else:
            return []

    def getBbox(self, bbox):
        import time, sys

        sys.stderr.write("<!-- Start %s -->\n" % time.time())
        nodes = self.getNodesInBounds(bbox)
        sys.stderr.write("<!-- Get nodes %s -->\n" % time.time())
        ways = self.getWaysFromNodes(nodes)
        sys.stderr.write("<!-- Get ways %s -->\n" % time.time())

        wayNodes = self.getNodesFromWays(ways)
        for n in wayNodes:
            if n['id'] not in nodes:
                nodes.append(n)
        sys.stderr.write("<!-- Get nodes from ways %s -->\n" % time.time())

        relations = self.getRelationsFromWays(ways)
        sys.stderr.write("<!-- Get relations %s -->\n" % time.time())
        
        doc = {'bounds': {'minlat': bbox[0][0],
                          'minlon': bbox[0][1],
                          'maxlat': bbox[1][0],
                          'maxlon': bbox[1][1]},
               'nodes': nodes,
               'ways': ways,
               'relations': relations}

        return doc

class OsmXmlOutput:
    def defaultAttrs(self, mappableElement, mappable):
        mappableElement.setAttribute("id", str(mappable['id']))
        mappableElement.setAttribute("version", str(mappable['version']))
        mappableElement.setAttribute("user", mappable['user'])

    def tagNodes(self, doc, mappableElement, mappable):
        for tag in mappable['tags'].items():
            tagElement = doc.createElement("tag")
            tagElement.setAttribute("k", tag[0])
            tagElement.setAttribute("v", tag[1])
            mappableElement.appendChild(tagElement)

    def write(self, data):
        from xml.dom.minidom import Document

        doc = Document()
        root = doc.createElement("osm")
        root.setAttribute("generator", "mongosm 0.1")
        root.setAttribute("version", "0.6")
        doc.appendChild(root)

        bounds = doc.createElement("bounds")
        bounds.setAttribute("minlat", str(data['bounds']['minlat']))
        bounds.setAttribute("minlon", str(data['bounds']['minlon']))
        bounds.setAttribute("maxlat", str(data['bounds']['maxlat']))
        bounds.setAttribute("maxlon", str(data['bounds']['maxlon']))
        root.appendChild(bounds)

        for node in data['nodes']:
            nodeElem = doc.createElement("node")
            nodeElem.setAttribute("lat", str(node['loc']['lat']))
            nodeElem.setAttribute("lon", str(node['loc']['lon']))
            self.defaultAttrs(nodeElem, node)
            self.tagNodes(doc, nodeElem, node)
            root.appendChild(nodeElem)

        for way in data['ways']:
            wayElem = doc.createElement("way")
            self.defaultAttrs(wayElem, way)
            self.tagNodes(doc, wayElem, way)
            for ref in way['nodes']:
                refElement = doc.createElement("nd")
                refElement.setAttribute("ref", str(ref))
                wayElem.appendChild(refElement)
            root.appendChild(wayElem)

        for relation in data['relations']:
            relationElem = doc.createElement("relation")
            self.defaultAttrs(relationElem, relation)
            self.tagNodes(doc, relationElem, relation)
            for member in relation['members']:
                memberElem = doc.createElement("member")
                memberElem.setAttribute("type", member['type'])
                memberElem.setAttribute("ref", str(member['ref']))
                memberElem.setAttribute("role", member['role'])
                relationElem.appendChild(memberElem)
            root.appendChild(relationElem)

        print doc.toprettyxml(indent="  ")

if __name__ == '__main__':
    bbox = [[44.9699,-93.2789],[44.9829,-93.2612]]
    api = OsmApi()
    data = api.getBbox(bbox)
    
    outputter = OsmXmlOutput()
    outputter.write(data)
