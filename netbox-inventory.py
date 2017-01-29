#! /usr/bin/python

import os
import re
import sys
import json
import yaml
import urllib
import argparse


class Script(object):
    #
    # Script options.
    def cliArguments(self):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument("-c","--config-file", default="netbox-inventory.yml", help="Path for configuration of the script.")
        parser.add_argument("-t", "--test-sample", default="api_sample.json", action="store_true",
                            help="Test sample of API output instead connect to the real API.")
        parser.add_argument("--list", "--ansible", help="Print output as Ansible dynamic inventory syntax.", action="store_true")
        cliArguments = parser.parse_args()
        return cliArguments

    #
    # Open Yaml file.
    def openYamlFile(self, yamlFile):
        # Check if procs list file exists.
        try:
            os.path.isfile(yamlFile)
        except TypeError:
            print "Cannot open YAML file: %s." % (yamlFile)
            sys.exit(1)

        # Load content of Yaml file.
        with open(yamlFile, 'r') as procsYamlFile:
            try:
                yamlFileContent = yaml.load(procsYamlFile)
            except yaml.YAMLError as yamlError:
                print(yamlError)
        #
        return yamlFileContent

#
class Utils(object):
    #
    def getValueByPath(self, sourceDict, keyPath, ignoreKeyError=False):
        try:
            keyOutput = reduce(lambda xdict, key: xdict[key], keyPath.split('.'), sourceDict)
        except KeyError, keyName:
            if ignoreKeyError:
                keyOutput = None
            else:
                print "The key %s is not found. Please remember, Python is case sensitive." % (keyName)
                sys.exit(1)
        except TypeError:
            keyOutput = None
        return keyOutput

#
class NetboxInventory(object):
    def __init__(self, configData):
        self.defaults = configData.get("defaults")
        self.api_url = self.defaults.get('api_url')
        self.groupBy = configData.get("groupBy")
        self.utils = Utils()
        self.hostsVarsDict = configData.get("hostsVars")


    def getHostsList(self):
        ''''''
        dataSource = self.api_url
        jsonData = urllib.urlopen(dataSource).read()
        allHostsList = json.loads(jsonData)
        return allHostsList


    def addHostToInvenoryGroups(self, groupsCategories, inventoryDict, hostData):
        ''''''
        serverName = hostData.get("name")
        serverCF = hostData.get("custom_fields")
        groupCategories = self.groupBy

        for category in groupCategories:
            if category == 'default':
                dataDict = hostData
                keyName = "name"
            elif category == 'custom':
                dataDict = serverCF
                keyName = "value"

            for group in groupCategories[category]:
                groupValue = self.utils.getValueByPath(dataDict, group + "." + keyName)

            if groupValue:
                if not inventoryDict.has_key(groupValue):
                    inventoryDict.update({groupValue: []})

                if serverName not in inventoryDict[groupValue]:
                    inventoryDict[groupValue].append(serverName)
        return inventoryDict


    def getHostVars(self, hostData, hostVars):
        ''''''
        hostVarsDict = dict()
        for category in hostVars:
            if category == 'ip':
                dataDict = hostData
                keyName = "address"
            elif category == 'general':
                dataDict = hostData
                keyName = "name"
            elif category == 'custom':
                dataDict = hostData.get("custom_fields")
                keyName = "value"

            for key, value in hostVars[category].iteritems():
                varName = key
                varValue = self.utils.getValueByPath(dataDict, value + "." + keyName, ignoreKeyError=True)
                if varValue:
                    if value in hostVars["ip"].values():
                        varValue = varValue.split("/")[0]
                    hostVarsDict.update({varName: varValue})
        return hostVarsDict

    def updateHostMeta(self, inventoryDict, hostName, hostVars):
        ''''''
        if hostVars:
            inventoryDict['_meta']['hostvars'].update({hostName: hostVars})

    def generateInventory(self):
        ''''''
        ansibleInvenory = {"_meta": {"hostvars": {}}}
        netboxHostsList = self.getHostsList()

        for currentHost in netboxHostsList:
            serverName = currentHost.get("name")
            serverIP = self.utils.getValueByPath(currentHost, "primary_ip.address")
            self.addHostToInvenoryGroups(self.groupBy, ansibleInvenory, currentHost)
            hostVars = self.getHostVars(currentHost, self.hostsVarsDict)
            self.updateHostMeta(ansibleInvenory, serverName, hostVars)
        return json.dumps(ansibleInvenory)

#
if __name__ == "__main__":
    # Srcipt vars.
    script = Script()
    args = script.cliArguments()
    configData = script.openYamlFile(args.config_file)

    # Netbox vars.
    netbox = NetboxInventory(configData)
    ansibleInventory = netbox.generateInventory()
    if args.list:
        print ansibleInventory
