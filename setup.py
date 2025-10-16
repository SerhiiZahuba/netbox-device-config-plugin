from setuptools import find_packages, setup

setup(
    name='netbox-device-config',
    version='1.0.0',
    description='NetBox plugin for fetching and storing MikroTik configs via Netmiko',
    author='Serhii Zahuba',
    author_email='serhii@example.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'netmiko>=4.3.0',
    ],
    zip_safe=False,
)
